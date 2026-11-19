"""Prepare and verify release reference-data assets without publishing anything."""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import tarfile
import tempfile
from urllib.parse import quote

import requests
import yaml


MAX_ASSET_SIZE = 2 * 1024**3 - 1
DEFAULT_PART_SIZE = 1900 * 1024**2
CHUNK_SIZE = 1024**2


def checksum(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(CHUNK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def check_file(path, record):
    if path.stat().st_size != record["size"] or checksum(path) != record["sha256"]:
        raise ValueError(f"Size or SHA-256 mismatch: {path}")


def download(url, destination):
    """Stream bytes verbatim; never let HTTP content decoding alter an archive."""
    with requests.get(url, stream=True, timeout=(10, 300),
                      headers={"Accept-Encoding": "identity"}) as response:
        response.raise_for_status()
        with open(destination, "wb") as output:
            for block in response.raw.stream(CHUNK_SIZE, decode_content=False):
                output.write(block)


def asset_name(name):
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", name) or name in (".", ".."):
        raise ValueError(f"Invalid asset name: {name!r}")
    return name


def load_lock(path):
    with open(path, encoding="utf-8") as source:
        lock = json.load(source)
    if lock.get("schema_version") != 1 or not lock.get("install_files"):
        raise ValueError("Unsupported or empty reference-data lock")
    release_url(lock, "validation")
    seen = set()
    for definition in lock["install_files"].values():
        if not definition.get("archives"):
            raise ValueError("Locked dataset has no archives")
        for archive in definition["archives"]:
            asset_name(archive["name"])
            records = [archive] + archive["parts"]
            if not archive["parts"] or sum(p["size"] for p in archive["parts"]) != archive["size"]:
                raise ValueError("Invalid archive parts")
            for record in records:
                if record["size"] < 0 or not re.fullmatch(r"[a-f0-9]{64}", record["sha256"]):
                    raise ValueError("Invalid size or SHA-256")
            for part in archive["parts"]:
                name = asset_name(part["name"])
                if name in seen or part["size"] > MAX_ASSET_SIZE:
                    raise ValueError("Duplicate or oversized release asset")
                seen.add(name)
    return lock


def release_url(lock, name):
    repository = lock["repository"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Invalid GitHub repository")
    if not isinstance(lock["release"], str) or not re.fullmatch(r"\S+", lock["release"]):
        raise ValueError("Invalid release tag")
    return f"https://github.com/{repository}/releases/download/{quote(lock['release'], safe='')}/{asset_name(name)}"


def assemble(archive, destination, get_part):
    """Verify every part and the joined archive before returning it for extraction."""
    destination = Path(destination)
    try:
        with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
            with destination.open("wb") as output:
                for part in archive["parts"]:
                    path = Path(temporary) / asset_name(part["name"])
                    get_part(part, path)
                    check_file(path, part)
                    with path.open("rb") as source:
                        for block in iter(lambda: source.read(CHUNK_SIZE), b""):
                            output.write(block)
                    # A multi-GiB archive must not retain all temporary parts.
                    path.unlink()
        check_file(destination, archive)
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def prepare(manifest, output, repository, release, packages=None, part_size=DEFAULT_PART_SIZE):
    if not 0 < part_size <= MAX_ASSET_SIZE:
        raise ValueError("Part size must be positive and below 2 GiB")
    with open(manifest, encoding="utf-8") as source:
        lock = copy.deepcopy(yaml.safe_load(source))
    definitions = lock["install_files"]
    selected = list(definitions) if packages == ["all"] else (packages or ["pandeia_data", "pandeia_psf"])
    unknown = set(selected) - definitions.keys()
    if unknown:
        raise ValueError(f"Unknown packages: {sorted(unknown)}")
    lock["install_files"] = {name: definitions[name] for name in selected}
    lock.update(schema_version=1, repository=repository, release=release)
    release_url(lock, "validation")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError("Snapshot output directory must be empty (avoid stale assets)")
    for package, definition in lock["install_files"].items():
        asset_name(package)
        urls = definition.pop("data_url")
        if isinstance(urls, str):
            urls = [urls]
        definition["archives"] = []
        for index, url in enumerate(urls, 1):
            name = f"refdata-{package}-{index:03d}.tar"
            print(f"Snapshotting {package} archive {index}/{len(urls)}...", flush=True)
            with tempfile.TemporaryDirectory(dir=output) as temporary:
                original = Path(temporary) / name
                download(url, original)
                archive = dict(name=name, source_url=url, size=original.stat().st_size,
                               sha256=checksum(original), parts=[])
                with original.open("rb") as source:
                    remaining = archive["size"]
                    number = 1
                    while remaining or not archive["parts"]:
                        part_name = name if archive["size"] <= part_size else f"{name}.part{number:05d}"
                        path = output / part_name
                        count = min(remaining, part_size)
                        with path.open("wb") as target:
                            left = count
                            while left:
                                block = source.read(min(CHUNK_SIZE, left))
                                target.write(block)
                                left -= len(block)
                        archive["parts"].append(dict(name=part_name, size=count, sha256=checksum(path)))
                        remaining -= count
                        number += 1
                definition["archives"].append(archive)
                print(f"Prepared {archive['size']:,} bytes in {len(archive['parts'])} asset(s)", flush=True)
    path = output / "refdata-lock.json"
    path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    load_lock(path)
    return path


def verify(lock_path, assets):
    lock = load_lock(lock_path)
    with tempfile.TemporaryDirectory() as temporary:
        for definition in lock["install_files"].values():
            for archive in definition["archives"]:
                def get_part(part, target):
                    shutil.copyfile(Path(assets) / asset_name(part["name"]), target)
                destination = Path(temporary) / archive["name"]
                assemble(archive, destination, get_part)
                # Catch HTML/error documents returned with HTTP 200 upstream.
                with tarfile.open(destination) as tarball:
                    for member in tarball:
                        pass
                destination.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    snapshot = commands.add_parser("prepare")
    snapshot.add_argument("--manifest", default="refdata_dependencies.yaml")
    snapshot.add_argument("--output", default="refdata-assets")
    snapshot.add_argument("--repository", required=True)
    snapshot.add_argument("--release", required=True)
    snapshot.add_argument("--packages", nargs="+", default=["pandeia_data", "pandeia_psf"])
    snapshot.add_argument("--part-size", type=int, default=DEFAULT_PART_SIZE)
    validation = commands.add_parser("verify")
    validation.add_argument("--lock", default="refdata-lock.json")
    validation.add_argument("--assets", default="refdata-assets")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.manifest, args.output, args.repository, args.release, args.packages, args.part_size)
    else:
        verify(args.lock, args.assets)


if __name__ == "__main__":
    main()
