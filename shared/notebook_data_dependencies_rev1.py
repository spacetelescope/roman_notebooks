import os
import requests
import tarfile
import yaml


def install_files(
    dependencies="https://raw.githubusercontent.com/spacetelescope/roman_notebooks/refs/heads/main/refdata_dependencies.yaml",
    verbose=True,
    packages=None,
):
    """
    Retrieve ancillary reference data files needed for specific Python packages.

    Parameters
    ----------
    dependencies : str
        Path to a local YAML file or URL containing the 'install_files' section.
    verbose : bool
        If True, print progress messages.
    packages : str or list[str] or None
        If provided, limit installation to these package keys. Can be a
        comma-separated string or a list of package names.

    Returns
    -------
    result : dict
        Mapping of environment-variable name -> {"path": <str>, "pre_installed": <bool>}.
    """
    # Load YAML from local file or URL
    if os.path.exists(dependencies):
        if verbose:
            print(f"Loading dependencies from local file: {dependencies}")
        with open(dependencies, "r") as f:
            yf = yaml.safe_load(f)["install_files"]
    else:
        if verbose:
            print(f"Downloading dependencies YAML from: {dependencies}")
        r = requests.get(dependencies, allow_redirects=True)
        r.raise_for_status()
        yf = yaml.safe_load(r.content)["install_files"]

    # Optionally limit to specific packages
    if packages:
        if isinstance(packages, str):
            packages = [p.strip() for p in packages.split(",") if p.strip()]
        keys = list(yf.keys())
        for k in keys:
            if k not in packages:
                yf.pop(k, None)
        if verbose:
            print(f"Limiting installation to packages: {packages}")

    home = os.environ.get("HOME", "")
    result = {}

    for package, info in yf.items():
        envvar = info["environment_variable"]
        try:
            current = os.environ[envvar]
            if current == "***unset***":
                raise KeyError("UNSET PATH")
            if verbose:
                print(f"Found {package} path in environment: {envvar}={current}")
            result[envvar] = {"path": current, "pre_installed": True}
        except KeyError:
            if verbose:
                print(f"Did not find {package} data in environment, setting it up...")

            # Resolve install path (expand ${HOME})
            env_path = info["install_path"]
            parts = []
            for part in env_path.split("/"):
                if "${HOME}" in part and home:
                    parts.append(home)
                else:
                    parts.append(part)
            final_path = "/".join(parts)

            # Ensure directory exists
            os.makedirs(final_path, exist_ok=True)

            # Download and extract each tarball using streaming I/O
            urls = info.get("data_url", [])
            if verbose:
                print(f"\tInstalling to: {final_path}")
                print(f"\tFound {len(urls)} data URL(s) to download and install...")
            for i, url in enumerate(urls, start=1):
                if verbose:
                    print(f"\t  [{i}/{len(urls)}] Downloading: {url}")
                file_name = url.rsplit("/", 1)[-1]

                # Stream download to avoid large memory usage
                with requests.get(url, stream=True) as resp:
                    resp.raise_for_status()
                    with open(file_name, "wb") as download_file:
                        for chunk in resp.iter_content(chunk_size=8192):
                            if chunk:
                                download_file.write(chunk)

                if verbose:
                    print(f"\t  Extracting: {file_name}")
                with tarfile.open(file_name) as tarball:
                    tarball.extractall(path=final_path)
                os.remove(file_name)

            data_path = info["data_path"]
            full_path = os.path.join(final_path, data_path)

            if verbose:
                print("\tUpdate environment variable with the following:")
                print(f"\t  export {envvar}='{full_path}'")

            result[envvar] = {"path": full_path, "pre_installed": False}

    return result


def setup_env(result, verbose=True):
    """
    Set environment variables in this process and log paths.

    Parameters
    ----------
    result : dict
        Mapping of env var -> {"path": <str>, "pre_installed": <bool>}.
    verbose : bool
        If True, print the resulting paths.
    """
    if verbose:
        print("Reference data paths set to (in this process):")

    for k, v in result.items():
        # Only override env var in this process if we just installed it
        if not v["pre_installed"]:
            os.environ[k] = v["path"]

        if verbose:
            print(f"\t{k} = {v['path']}")


if __name__ == "__main__":
    # Download data and compute paths
    result = install_files()

    # Set them in the current Python process (for any child processes spawned from here)
    setup_env(result)

    # Persist environment variables for the GitHub Actions job, if available
    github_env = os.environ.get("GITHUB_ENV")
    if github_env:
        print(f"Writing environment variables to GITHUB_ENV: {github_env}")
        with open(github_env, "a") as fh:
            for k, v in result.items():
                fh.write(f"{k}={v['path']}\n")
    else:
        # Fallback for local execution where GITHUB_ENV is not defined
        print("GITHUB_ENV not set; printing KEY=VALUE lines instead:")
        for k, v in result.items():
            print(f"{k}={v['path']}")
