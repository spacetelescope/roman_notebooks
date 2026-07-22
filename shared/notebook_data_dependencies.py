import os
from pathlib import Path
import tarfile
import tempfile

import requests
import yaml


_MANIFEST_NAME = "refdata_dependencies.yaml"
_MANIFEST_ENV_VAR = "ROMAN_REFDATA_MANIFEST"


def _resolve_dependencies(dependencies=None):
    """
    Resolve the reference-data manifest used by the checked-out repository.

    Resolution order:
    1. An explicitly supplied local path or URL.
    2. The ROMAN_REFDATA_MANIFEST environment variable.
    3. refdata_dependencies.yaml beside the checked-out repository.
    4. refdata_dependencies.yaml in the current working directory.

    Mutable GitHub branches such as ``main`` are deliberately not used as a
    fallback because their manifest may not match the checked-out release.
    """
    if dependencies:
        return str(dependencies)

    override = os.environ.get(_MANIFEST_ENV_VAR)
    if override:
        return override

    module_path = Path(__file__).resolve()
    candidates = [
        module_path.parent.parent / _MANIFEST_NAME,
        Path.cwd() / _MANIFEST_NAME,
    ]

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    checked = "\n".join(f"  - {candidate}" for candidate in candidates)
    raise FileNotFoundError(
        f"Could not locate {_MANIFEST_NAME}.\n"
        f"Checked:\n{checked}\n"
        f"Set {_MANIFEST_ENV_VAR} to an explicit local path or URL if the "
        "manifest is stored elsewhere."
    )


def _load_yaml(dependencies=None):
    """Load the dependency manifest from a local path or URL."""
    dependencies = _resolve_dependencies(dependencies)

    if os.path.isfile(dependencies):
        with open(dependencies, "r", encoding="utf-8") as manifest:
            return yaml.safe_load(manifest)

    if dependencies.startswith(("http://", "https://")):
        response = requests.get(
            dependencies,
            allow_redirects=True,
            timeout=(10, 60),
        )
        response.raise_for_status()
        return yaml.safe_load(response.content)

    raise FileNotFoundError(
        f"Dependency manifest does not exist: {dependencies}"
    )


def install_files(dependencies=None, verbose=True, packages=None):
    """
    Retrieve ancillary reference-data files needed by notebook packages.

    Parameters
    ----------
    dependencies : str or pathlib.Path, optional
        A local path or URL for the dependency manifest. When omitted, the
        manifest belonging to the checked-out repository is used.

        An explicit manifest can also be supplied through the
        ROMAN_REFDATA_MANIFEST environment variable.

    verbose : bool, optional
        Print installation messages.

    packages : None, list, or str, optional
        Packages for which reference data should be installed. This may be a
        list of package names, a comma-separated string, or None. When None,
        data for every package in the manifest is installed.

    Returns
    -------
    dict
        Environment-variable names mapped to their installed paths and
        whether those paths were already configured.
    """
    manifest = _load_yaml(dependencies)
    install_definitions = manifest["install_files"]

    if packages:
        if isinstance(packages, str):
            packages = [
                package.strip()
                for package in packages.split(",")
                if package.strip()
            ]

        install_definitions = {
            package: definition
            for package, definition in install_definitions.items()
            if package in packages
        }

    home = os.environ.get("HOME", os.path.expanduser("~"))
    result = {}

    for package, definition in install_definitions.items():
        envvar = definition["environment_variable"]
        existing_path = os.environ.get(envvar)

        if existing_path and existing_path != "***unset***":
            if verbose:
                print(f"Found {package} path {existing_path}")

            result[envvar] = {
                "path": existing_path,
                "pre_installed": True,
            }
            continue

        if verbose:
            print(
                f"Did not find {package} data in environment, "
                "setting it up..."
            )

        install_path = str(definition["install_path"]).replace(
            "${HOME}",
            home,
        )
        os.makedirs(install_path, exist_ok=True)

        data_urls = definition["data_url"]
        if isinstance(data_urls, str):
            data_urls = [data_urls]

        total_files = len(data_urls)

        if verbose:
            print("\tDownloading and uncompressing file...")
            print(
                f"\tFound {total_files} data URL(s) to download "
                "and install..."
            )

        for index, url in enumerate(data_urls, start=1):
            if verbose:
                print(f"\tWorking on file {index} out of {total_files}")

            response = requests.get(
                url,
                allow_redirects=True,
                stream=True,
                timeout=(10, 300),
            )
            response.raise_for_status()

            with tempfile.NamedTemporaryFile(
                dir=install_path,
                suffix=".tar.gz",
                delete=False,
            ) as temporary_file:
                temporary_name = temporary_file.name

                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        temporary_file.write(chunk)

            try:
                with tarfile.open(temporary_name) as tarball:
                    tarball.extractall(
                        path=install_path,
                        filter="data",
                    )
            finally:
                os.remove(temporary_name)

        data_path = os.path.join(
            install_path,
            definition["data_path"],
        )

        if verbose:
            print("\tUpdate environment variable with the following:")
            print(f"\t\texport {envvar}='{data_path}'")

        result[envvar] = {
            "path": data_path,
            "pre_installed": False,
        }

    return result


def setup_env(result, dependencies=None, verbose=True):
    """
    Apply installed reference-data paths and other manifest variables.

    Parameters
    ----------
    result : dict
        The dictionary returned by install_files().

    dependencies : str or pathlib.Path, optional
        A local path or URL for the dependency manifest. When omitted, the
        manifest belonging to the checked-out repository is used.

    verbose : bool, optional
        Print the environment variables being configured.
    """
    print("Reference data paths set to:")

    for key, value in result.items():
        if not value["pre_installed"]:
            os.environ[key] = value["path"]

        print(f"\t{key} = {value['path']}")

    manifest = _load_yaml(dependencies)
    other_variables = manifest.get("other_variables", {})
    home = os.environ.get("HOME", os.path.expanduser("~"))

    for key, value in other_variables.items():
        resolved_value = str(value).replace("${HOME}", home)
        existing_value = os.environ.get(key)

        if not existing_value:
            os.environ[key] = resolved_value

            if verbose:
                print(f"\t{key} = {resolved_value}")
        elif verbose:
            print(
                f"\t{key} = {existing_value} "
                "(pre-set, not overwritten)"
            )


if __name__ == "__main__":
    installation_result = install_files()
    setup_env(installation_result)
