import os
import requests
import tarfile
import yaml
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_yaml(start=None):
    """Walk up the directory tree to find refdata_dependencies.yaml.

    Starts from *start* (default: the directory containing this script) and
    checks each parent up to 5 levels.  Returns the Path on success or None.
    """
    current = Path(start).resolve() if start else Path(__file__).resolve().parent
    for _ in range(6):  # check current + 5 parents
        candidate = current / "refdata_dependencies.yaml"
        if candidate.exists():
            return candidate
        current = current.parent
    return None


def _load_yaml(dependencies=None, verbose=True):
    """Load the full YAML configuration dict.

    Resolution order:
      1. Explicit *dependencies* path/URL (if given)
      2. Walk up from this script to find a local refdata_dependencies.yaml
      3. Fall back to the GitHub main-branch URL
    """
    # 1. Explicit argument
    if dependencies and os.path.exists(dependencies):
        if verbose:
            print(f"Loading dependencies YAML from: {dependencies}")
        with open(dependencies, 'r') as f:
            return yaml.safe_load(f)

    # 2. Search the local repo tree
    found = _find_yaml()
    if found:
        if verbose:
            print(f"Loading dependencies YAML from repo: {found}")
        with open(found, 'r') as f:
            return yaml.safe_load(f)

    # 3. GitHub fallback
    url = ('https://raw.githubusercontent.com/spacetelescope/'
           'roman_notebooks/refs/heads/main/refdata_dependencies.yaml')
    if verbose:
        print(f"Local YAML not found; fetching from GitHub: {url}")
    req = requests.get(url, allow_redirects=True)
    req.raise_for_status()
    return yaml.safe_load(req.content)


# ---------------------------------------------------------------------------
# Main installer
# ---------------------------------------------------------------------------

def install_files(dependencies=None, verbose=True, packages=None):
    """
    Retrieve ancillary reference data files needed for specific Python
    packages (pandeia, STIPS, STPSF, synphot).

    For each package listed in the YAML, checks whether the corresponding
    environment variable already exists.  If not, downloads and extracts
    the reference tarballs, then returns a dict of paths to be set.

    Parameters
    ----------
    dependencies : str, optional
        Path or URL to the YAML definition file.  When *None* the file is
        located automatically (see ``_load_yaml``).
    verbose : bool
        Print progress messages. Default True.
    packages : None, list, or str
        Limit installation to these YAML keys.  Accepts a list of strings,
        a comma-separated string, or None (install everything).

    Returns
    -------
    dict
        ``{env_var: {'path': str, 'pre_installed': bool}}``
    """
    full_yaml = _load_yaml(dependencies, verbose=verbose)
    yf = dict(full_yaml.get('install_files', {}))   # shallow copy

    # Package filter
    if packages:
        if isinstance(packages, str):
            packages = [p.strip() for p in packages.split(',')]
        yf = {k: v for k, v in yf.items() if k in packages}

    home = os.environ.get('HOME', str(Path.home()))
    result = {}

    for package, info in yf.items():
        envvar = info['environment_variable']

        # Already configured?
        existing = os.environ.get(envvar, '')
        if existing and existing != '***unset***':
            if verbose:
                print(f"Found {package} path: {envvar}={existing}")
            result[envvar] = {'path': existing, 'pre_installed': True}
            continue

        if verbose:
            print(f"Did not find {package} data in environment, setting it up...")

        # Resolve install path
        env_path = info['install_path'].replace('${HOME}', home)
        os.makedirs(env_path, exist_ok=True)

        # Download and extract each tarball
        urls = info.get('data_url', [])
        if verbose:
            print(f"\tDownloading and uncompressing file...")
            print(f"\tFound {len(urls)} data URL(s) to download and install...")
        for i, url in enumerate(urls, start=1):
            if verbose:
                print(f"\tWorking on file {i} out of {len(urls)}")
            req = requests.get(url, allow_redirects=True)
            file_name = url.split('/')[-1]
            with open(file_name, 'wb') as fh:
                fh.write(req.content)
            with tarfile.open(file_name) as tarball:
                tarball.extractall(path=env_path)
            os.remove(file_name)

        final_path = os.path.join(env_path, info['data_path'])
        if verbose:
            print(f"\tUpdate environment variable with the following:")
            print(f"\t\texport {envvar}='{final_path}'")
        result[envvar] = {'path': final_path, 'pre_installed': False}

    return result


# ---------------------------------------------------------------------------
# Environment setup
# ---------------------------------------------------------------------------

def setup_env(result, dependencies=None, verbose=True):
    """Set environment variables from install_files() result AND from
    the ``other_variables`` YAML section (CRDS config, etc.).

    Parameters
    ----------
    result : dict
        Return value of ``install_files()``.
    dependencies : str, optional
        Explicit YAML path; when *None*, discovered automatically.
    verbose : bool
        Print variable assignments.
    """
    if verbose:
        print('Reference data paths set to:')

    # 1. Set reference-data paths
    for k, v in result.items():
        if not v['pre_installed']:
            os.environ[k] = v['path']
        if verbose:
            print(f"\t{k} = {v['path']}")

    # 2. Set other_variables (CRDS, etc.) if not already present
    yaml_path = dependencies or _find_yaml()
    if yaml_path and os.path.exists(str(yaml_path)):
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        home = os.environ.get('HOME', str(Path.home()))
        for k, v in data.get('other_variables', {}).items():
            if not os.environ.get(k):  # treat empty string as unset
                resolved = str(v).replace('${HOME}', home)
                os.environ[k] = resolved
                if verbose:
                    print(f"\t{k} = {resolved}")
            elif verbose:
                print(f"\t{k} = {os.environ[k]} (already set)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    result = install_files()
    setup_env(result)
