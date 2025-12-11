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

    Returns
    -------
    result : dict
        Mapping of environment-variable name -> {"path": <str>, "pre_installed": <bool>}.
    """
    # Load YAML from local file or URL
    if os.path.exists(dependencies):
        with open(dependencies, "r") as f:
            yf = yaml.safe_load(f)["install_files"]
    else:
        req = requests.get(dependencies, allow_redirects=True)
        req.raise_for_status()
        yf = yaml.safe_load(req.content)["install_files"]

    # Optionally limit to specific packages
    if packages:
        if isinstance(packages, str):
            packages = [p.strip() for p in packages.split(",") if p.strip()]
        keys = list(yf.keys())
        for k in keys:
            if k not in packages:
                yf.pop(k, None)

    home = os.environ.get("HOME", "")
    result = {}

    for package, info in yf.items():
        envvar = info["environment_variable"]
        try:
            current = os.environ[envvar]
            if current == "***unset***":
                raise KeyError("UNSET PATH")
            if verbose:
                print(f"Found {package} path {current}")
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

            # Download and extract each tarball
            urls = info.get("data_url", [])
            if verbose:
                print(f"\tDownloading and uncompressing file...")
                print(f"\tFound {len(urls)} data URL(s) to download and install...")
            for i, url in enumerate(urls, start=1):
                if verbose:
                    print(f"\tWorking on file {i} out of {len(urls)}")
                r = requests.get(url, allow_redirects=True)
                r.raise_for_status()
                file_name = url.rsplit("/", 1)[-1]
                with open(file_name, "wb") as download_file:
                    download_file.write(r.content)
                with tarfile.open(file_name) as tarball:
                    tarball.extractall(path=final_path)
                os.remove(file_name)

            data_path = info["data_path"]
            full_path = os.path.join(final_path, data_path)

            if verbose:
                print("\tUpdate environment variable with the following:")
                print(f"\t\texport {envvar}='{full_path}'")

            result[envvar] = {"path": full_path, "pre_installed": False}

    return result


def setup_env(result):
    """Set env vars in this process and log paths."""
    print("Reference data paths set to:")
    for k, v in result.items():
        if not v["pre_installed"]:
            os.environ[k] = v["path"]
        print(f"\t{k} = {v['path']}")


if __name__ == "__main__":
    # Download data and compute paths
    result = install_files()
    # Optionally set them in this Python process (for any child processes)
    setup_env(result)
    # Emit KEY=VALUE lines for the GitHub Actions workflow to consume
    for k, v in result.items():
        print(f"{k}={v['path']}")
