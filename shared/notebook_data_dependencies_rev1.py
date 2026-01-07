import os
import time
import tarfile
import yaml
import gzip
import shutil
import math
import requests

from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# -------------------------
# HTTP session w/ retries
# -------------------------
def make_session(
    total_retries=5,
    backoff_factor=0.8,
    status_forcelist=(429, 500, 502, 503, 504),
):
    session = requests.Session()
    retry = Retry(
        total=total_retries,
        connect=total_retries,
        read=total_retries,
        status=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods={"GET", "HEAD"},
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


# -------------------------
# Helpers
# -------------------------
def human_bytes(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f}{unit}" if unit != "B" else f"{int(n)}B"
        n /= 1024.0


def safe_remove(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


# -------------------------
# Single-stream download
# -------------------------
def download_with_progress(
    session,
    url,
    dest_path,
    verbose=True,
    timeout=(10, 300),          # (connect, read)
    chunk_size=256 * 1024,      # 256KB
    progress_every_sec=1,
):
    t0 = time.time()
    last_print = t0
    bytes_done = 0

    with session.get(url, stream=True, timeout=timeout, allow_redirects=True) as resp:
        resp.raise_for_status()

        total = resp.headers.get("Content-Length")
        total = int(total) if total and total.isdigit() else None

        if verbose:
            print("    Connection established, waiting for first bytes...", flush=True)

        os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)

        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                f.write(chunk)
                bytes_done += len(chunk)

                now = time.time()
                if verbose and (now - last_print) >= progress_every_sec:
                    elapsed = max(now - t0, 1e-6)
                    speed = bytes_done / elapsed

                    if total:
                        pct = (bytes_done / total) * 100
                        remaining = max(total - bytes_done, 0)
                        eta = remaining / max(speed, 1e-6)
                        print(
                            f"    {pct:5.1f}%  {human_bytes(bytes_done)}/{human_bytes(total)}  "
                            f"{human_bytes(speed)}/s  ETA ~{int(eta)}s",
                            flush=True,
                        )
                    else:
                        print(
                            f"    {human_bytes(bytes_done)} downloaded  {human_bytes(speed)}/s",
                            flush=True,
                        )
                    last_print = now

    if verbose:
        elapsed = max(time.time() - t0, 1e-6)
        print(
            f"    Finished: {human_bytes(bytes_done)} in {elapsed:.1f}s "
            f"({human_bytes(bytes_done/elapsed)}/s)",
            flush=True,
        )


# -------------------------
# Parallel range download
# -------------------------
def _head_info(session, url, timeout):
    # Prefer HEAD; fall back to GET range 0-0 if some servers dislike HEAD.
    try:
        r = session.head(url, allow_redirects=True, timeout=timeout)
        if r.status_code < 400:
            return r.headers, r.status_code
    except requests.RequestException:
        pass

    try:
        r = session.get(
            url,
            headers={"Range": "bytes=0-0"},
            stream=True,
            allow_redirects=True,
            timeout=timeout,
        )
        return r.headers, r.status_code
    except requests.RequestException:
        return {}, 0


def _download_range_to_part(
    session,
    url,
    part_path,
    start,
    end,
    timeout,
    chunk_size=256 * 1024,
):
    headers = {"Range": f"bytes={start}-{end}"}
    written = 0
    with session.get(url, headers=headers, stream=True, allow_redirects=True, timeout=timeout) as r:
        r.raise_for_status()
        with open(part_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                f.write(chunk)
                written += len(chunk)
    return written


def download_parallel_with_progress(
    session,
    url,
    dest_path,
    verbose=True,
    timeout=(10, 300),
    workers=8,
    chunk_size=256 * 1024,
    progress_every_sec=1,
    min_size_for_parallel=50 * 1024 * 1024,  # 50MB
):
    """
    Parallel download using Range requests.
    Streams each range to its own .part file on disk, then concatenates.
    If server doesn't support Range or content length is unknown, falls back to single stream.
    """
    headers, _status = _head_info(session, url, timeout=timeout)
    accept_ranges = (headers.get("Accept-Ranges", "") or "").lower()
    total_str = headers.get("Content-Length", "")
    total = int(total_str) if total_str.isdigit() else None

    if not total or total < min_size_for_parallel:
        if verbose:
            why = "unknown Content-Length" if not total else f"file is small ({human_bytes(total)})"
            print(f"    Parallel download disabled ({why}); using single stream.", flush=True)
        return download_with_progress(
            session, url, dest_path, verbose=verbose, timeout=timeout,
            chunk_size=chunk_size, progress_every_sec=progress_every_sec
        )

    if accept_ranges and "bytes" not in accept_ranges:
        if verbose:
            print("    Server does not advertise byte ranges; using single stream.", flush=True)
        return download_with_progress(
            session, url, dest_path, verbose=verbose, timeout=timeout,
            chunk_size=chunk_size, progress_every_sec=progress_every_sec
        )

    workers = max(1, min(int(workers), 32))

    part_size = int(math.ceil(total / workers))
    ranges = []
    for i in range(workers):
        start = i * part_size
        end = min(start + part_size - 1, total - 1)
        if start > end:
            break
        ranges.append((i, start, end))

    if verbose:
        print(f"    Parallel download: {len(ranges)} parts, total {human_bytes(total)}", flush=True)
        print("    Connection established, downloading ranges...", flush=True)

    os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)

    part_paths = []
    for i, _, _ in ranges:
        p = f"{dest_path}.part{i:02d}"
        part_paths.append(p)
        safe_remove(p)
    safe_remove(dest_path)

    t0 = time.time()
    last_print = t0

    def total_downloaded_so_far():
        s = 0
        for p in part_paths:
            try:
                s += os.path.getsize(p)
            except OSError:
                pass
        return s

    errors = []
    with ThreadPoolExecutor(max_workers=len(ranges)) as ex:
        futs = []
        for i, start, end in ranges:
            part_path = f"{dest_path}.part{i:02d}"
            futs.append(ex.submit(_download_range_to_part, session, url, part_path, start, end, timeout, chunk_size))

        pending = set(futs)
        while pending:
            done_now = {f for f in pending if f.done()}
            pending -= done_now

            now = time.time()
            if verbose and (now - last_print) >= progress_every_sec:
                got = total_downloaded_so_far()
                elapsed = max(now - t0, 1e-6)
                speed = got / elapsed
                pct = (got / total) * 100
                remaining = max(total - got, 0)
                eta = remaining / max(speed, 1e-6)
                print(
                    f"    {pct:5.1f}%  {human_bytes(got)}/{human_bytes(total)}  "
                    f"{human_bytes(speed)}/s  ETA ~{int(eta)}s",
                    flush=True,
                )
                last_print = now

            time.sleep(0.2)

        for f in futs:
            try:
                f.result()
            except Exception as e:
                errors.append(e)

    if errors:
        for p in part_paths:
            safe_remove(p)
        if verbose:
            print(f"    Parallel download failed ({errors[0]!r}); falling back to single stream.", flush=True)
        return download_with_progress(
            session, url, dest_path, verbose=verbose, timeout=timeout,
            chunk_size=chunk_size, progress_every_sec=progress_every_sec
        )

    if verbose:
        print("    Stitching parts...", flush=True)
    with open(dest_path, "wb") as out:
        for p in part_paths:
            with open(p, "rb") as f:
                shutil.copyfileobj(f, out, length=1024 * 1024)
            safe_remove(p)

    if verbose:
        got = total
        elapsed = max(time.time() - t0, 1e-6)
        print(
            f"    Finished: {human_bytes(got)} in {elapsed:.1f}s "
            f"({human_bytes(got/elapsed)}/s)",
            flush=True,
        )


# -------------------------
# Extract logic (UPDATED)
# -------------------------
def extract_archive(path, dest, verbose=True):
    """
    Extract supported archives into `dest`.

    Handles:
      - .tar, .tar.gz, .tgz -> extracted directly via tarfile (includes gzip handling)
      - .gz                 -> gunzip to a file, then:
                               * if the result is a tar (even without .tar extension), extract it
                               * otherwise leave the decompressed file in place
    """
    if path.endswith((".tar", ".tar.gz", ".tgz")):
        if verbose:
            print(f"    Extracting tar archive: {path}", flush=True)
        with tarfile.open(path) as tar:
            tar.extractall(dest)
        return

    if path.endswith(".gz"):
        if verbose:
            print(f"    Extracting gzip file: {path}", flush=True)

        os.makedirs(dest, exist_ok=True)

        # 1) gunzip to a file (strip .gz)
        out_file = os.path.join(dest, os.path.basename(path[:-3]))
        safe_remove(out_file)
        with gzip.open(path, "rb") as f_in, open(out_file, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

        # 2) If the gunzipped result is a tar archive, extract it too.
        #    This covers:
        #      - out_file ends with .tar
        #      - tar-without-extension (Box sometimes provides these)
        try:
            with tarfile.open(out_file) as tar:
                if verbose:
                    print(f"    Detected tar after gunzip, extracting: {out_file}", flush=True)
                tar.extractall(dest)
            safe_remove(out_file)  # remove the intermediate tar blob
        except tarfile.TarError:
            # Not a tar; keep the decompressed file as-is.
            if verbose:
                print(f"    Gunzipped to non-tar file: {out_file}", flush=True)
        return

    raise RuntimeError(f"Unknown archive format: {path}")


# -------------------------
# Main installer
# -------------------------
def install_files(
    dependencies="https://raw.githubusercontent.com/spacetelescope/roman_notebooks/refs/heads/main/refdata_dependencies.yaml",
    verbose=True,
    packages=None,
    timeout=(10, 300),       # read timeout bumped for slow servers
    retries=5,
    parallel_workers=8,
):
    session = make_session(total_retries=retries)

    # Load YAML
    if os.path.exists(dependencies):
        if verbose:
            print(f"Loading dependencies from local file: {dependencies}", flush=True)
        with open(dependencies, "r") as f:
            yf = yaml.safe_load(f)["install_files"]
    else:
        if verbose:
            print(f"Downloading dependencies YAML from: {dependencies}", flush=True)
        r = session.get(dependencies, timeout=timeout, allow_redirects=True)
        r.raise_for_status()
        yf = yaml.safe_load(r.content)["install_files"]

    # Package filter
    if packages:
        if isinstance(packages, str):
            packages = [p.strip() for p in packages.split(",") if p.strip()]
        for k in list(yf.keys()):
            if k not in packages:
                yf.pop(k)
        if verbose:
            print(f"Limiting installation to packages: {packages}", flush=True)

    home = os.environ.get("HOME", "")
    result = {}

    for package, info in yf.items():
        envvar = info["environment_variable"]

        # If env var already set (and not the sentinel), respect it
        try:
            current = os.environ[envvar]
            if current != "***unset***":
                if verbose:
                    print(f"Found {package} path in environment: {envvar}={current}", flush=True)
                result[envvar] = {"path": current, "pre_installed": True}
                continue
        except KeyError:
            pass

        if verbose:
            print(f"Did not find {package} data in environment, setting it up...", flush=True)

        env_path = info["install_path"].replace("${HOME}", home)
        os.makedirs(env_path, exist_ok=True)

        urls = info.get("data_url", [])
        if verbose:
            print(f"\tInstalling to: {env_path}", flush=True)
            print(f"\tFound {len(urls)} data URL(s) to download and install...", flush=True)

        for i, url in enumerate(urls, start=1):
            fname = url.rsplit("/", 1)[-1]
            tmp = os.path.join(env_path, f".download.{fname}.tmp")
            final = os.path.join(env_path, fname)

            if verbose:
                print(f"\t  [{i}/{len(urls)}] Downloading: {url}", flush=True)
                print(f"\t    -> {final}", flush=True)

            safe_remove(tmp)
            safe_remove(final)

            download_parallel_with_progress(
                session=session,
                url=url,
                dest_path=tmp,
                verbose=verbose,
                timeout=timeout,
                workers=parallel_workers,
            )

            os.replace(tmp, final)
            extract_archive(final, env_path, verbose=verbose)
            safe_remove(final)

        data_path = info["data_path"]
        full_path = os.path.join(env_path, data_path)

        # Fail fast if the expected directory doesn't exist.
        # This prevents "export STPSF_PATH=..." pointing to nowhere.
        if not os.path.isdir(full_path):
            raise RuntimeError(
                f"{package}: expected directory not created: {full_path}\n"
                f"Archive contents may not match YAML data_path ({data_path}). "
                f"Check extraction logic or adjust data_path."
            )

        if verbose:
            print(f"\tUpdate environment variable with the following:", flush=True)
            print(f"\t  export {envvar}='{full_path}'", flush=True)

        result[envvar] = {"path": full_path, "pre_installed": False}

    return result


# -------------------------
# Environment setup
# -------------------------
def setup_env(result, verbose=True):
    if verbose:
        print("Reference data paths set to (in this process):", flush=True)
    for k, v in result.items():
        if not v["pre_installed"]:
            os.environ[k] = v["path"]
        if verbose:
            print(f"\t{k} = {v['path']}", flush=True)


# -------------------------
# Entry point
# -------------------------
if __name__ == "__main__":
    result = install_files()
    setup_env(result)

    github_env = os.environ.get("GITHUB_ENV")
    if github_env:
        print(f"Writing environment variables to GITHUB_ENV: {github_env}", flush=True)
        with open(github_env, "a") as fh:
            for k, v in result.items():
                fh.write(f"{k}={v['path']}\n")
    else:
        print("GITHUB_ENV not set; printing KEY=VALUE lines instead:", flush=True)
        for k, v in result.items():
            print(f"{k}={v['path']}", flush=True)
