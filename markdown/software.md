# Installing Extra Software
The Roman Research Nexus (RRN) provides some pre-installed software. You can also install your own software.

**Note:** Any commands shown on this page must be entered into a terminal window. To open one, select **File → New → Terminal** from the JupyterLab menu bar. See [Working in JupyterLab](./jupyter.md) for more information about the interface.

## What software is installed?
To list packages in the currently active environment, run:

`conda list`

Since this list is lengthy, you can check the version of a specific package using:

`conda list <package>`

For example:

```bash
conda list astropy
conda list numpy
```

If you believe a package should be included by default, you can submit a request to the [Roman Help Desk](https://stsci.service-now.com/roman).

## How do I install and manage my own software?
When working in the Nexus, it is essential to create dedicated software environments. Packages installed in the default environment with

`pip install <package>`

may be lost when the server is restarted or reconfigured. Create a dedicated environment for software that must persist across sessions. For information about restarting and reconfiguring servers, see [Managing Your Server](./server.md).

On the RRN, you can use helper commands to create and manage software environments. Follow the steps below to set up your own environments and install packages.

### 1. Listing Environments

To list environments, including those you have installed manually, run:

`kernel-list`

### 2. Creating a Requirements File

You can record the packages to install in a pip requirements file (`requirements.txt`). Doing so makes your package installation reproducible and allows you to recreate or share it with collaborators.

The [pip documentation](https://pip.pypa.io/en/stable/reference/requirements-file-format/) describes the requirements file format. Below is an example:

```text
romancal>=1.0.1
roman_datamodels>=1.0.0
rad>=1.0.0
git+https://github.com/astropy/astroquery.git@refs/pull/3593/head
fsspec[s3]
matplotlib
```

In the example above, there are several important concepts to understand:

1. Version constraints

    Package versions can be specified using operators such as >, >=, ==, <, and <=. In general, it is best to specify versions as flexibly as possible so that the package solver can find compatible dependencies and avoid version conflicts. If a specific version is required, use the equality operator (==). If no version constraint is provided, the package manager will install the latest compatible version available.

2. Installing directly from a Git repository

    The astroquery package is installed directly from a GitHub source using:

    `git+https://github.com/astropy/astroquery.git@refs/pull/3593/head`


    In this example, the package is installed from a GitHub pull request rather than an official release. This approach can be useful when a required feature or bug fix has not yet been incorporated into a published release. More information about installing packages from Git repositories is available in the [pip documentation on VCS support](https://pip.pypa.io/en/stable/topics/vcs-support/).

3. Package extras

    The package `fsspec[s3]` uses the optional s3 extra. Extras allow package maintainers to define additional dependencies needed for specific functionality. For example, installing `fsspec[s3]` includes tools required for working with AWS S3 storage. Not all packages provide extras, but when they do, they are typically documented by the package maintainers. Another common example is:

    `dask[complete]`
    which installs additional dependencies that enable the full set of Dask features.

### 3. Creating a Conda Environment

```{note}
Installing new environments on the Nexus may take up to 20 minutes to complete. Updating packages within an existing environment is much faster.
```

Use the `kernel-create` command to generate an environment for your software. You can select your desired Python version and choose a name for the environment.

`kernel-create <environment-name> [<python-version>] [<lab-display-name>]`

The *environment name* is used in terminal commands, while *lab-display-name* is what appears when selecting a Notebook kernel.

**Example:** To create a Python 3.13 environment that will appear as “WFI Lightcurves” in Jupyter:

`kernel-create wfi-lc 3.13 "WFI Lightcurves"`

After the environment is created, you can activate it and install any additional packages as described in the following steps. This is the simplest approach when starting with a small number of packages.

Alternatively, if you already know which packages your environment requires, you can define them in a Conda environment file (`environment.yml`) and create the environment with those packages installed from the start. In this case, `<python-version>` is replaced with the path to the YAML file. See the [Conda documentation](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#exporting-environments-with-conda-export) for more information about creating and sharing environment specifications.

`kernel-create wfi-lc ./environment.yml "WFI Lightcurves"`

In the environment file, you specify the Python version and any packages that should be installed when the environment is created. Here is a simple example:

```yaml
name: wfi-lc  # optional
channels:
  - conda-forge
dependencies:
  - python=3.13
```

If using a YAML file, we recommend adding `pip`, `ipython`, `ipykernel`, and `uv` to the `dependencies` list. The resulting file would look as follows:

```yaml
name: wfi-lc
channels:
  - conda-forge
dependencies:
  - python=3.13
  - pip
  - ipykernel  # needed to run a Jupyter kernel
  - ipython
  - uv
```

These packages and their use are described in step 5 below.

Once the environment is created, proceed to the next step.

### 4. Activating an Environment

To install software, you must first activate the environment. Use the *environment name*, not the display name.

Continuing the example above, activation would be:

`source kernel-activate wfi-lc`

With the environment activated, you can install software.

### 5. Installing Base Tools

If these packages were not already installed through the `environment.yml` file, first install the tools needed for package management and interactive Python sessions. The command:

`conda install --yes pip ipython ipykernel uv`

These packages will be used later:

- `pip` for package management
- `IPython` for interactive Python sessions
- `ipykernel` for running a Jupyter kernel
- `uv`, an extremely fast, Rust-based package management tool for use with `pip`

Installation of `uv` is optional and can be skipped. The argument `--yes` answers any prompts with "yes" and removes the need for user interaction with the installation process.

### 6. Installing Software

Once an environment is activated, you can install the packages listed in your `requirements.txt` file with:

`uv pip install -r requirements.txt`

if using `uv`, or

`pip install -r requirements.txt`

if using standard `pip`. Make sure that the `requirements.txt` file is in the current working directory.

You can also install individual packages using `pip` as usual. For example:

`pip install lightkurve`

See step 8 to learn how to export a YAML file from an existing environment.

### 7. Switching to a Different Environment

You can switch to another environment using the source `kernel-activate` command and the environment name.
For example, upon logging into the Nexus, you may be in a different environment such as `roman_cal`. To instead activate the `wfi-lc` environment, use the following command:

`source kernel-activate wfi-lc`

When using Jupyter notebooks, all kernels you have defined will be available regardless of the command line environment.
See [Working in JupyterLab](./jupyter.md) for more information about creating and using notebooks.

### 8. Exporting an Environment
To export a custom environment for later use (e.g., after adding or updating packages), use the `kernel-export` command:

`kernel-export <environment-name> <output-file-name.yaml>`

For example:

`kernel-export wfi-lc wfi-lc-specs.yaml`

To create an environment from this YAML file, replace the Python version argument in Step 3 with the path to the YAML file.

### 9. Deleting an Environment

To remove an environment you no longer want, use:

`kernel-delete <environment-name>`

Example:

`kernel-delete wfi-lc`

### Other Notes
#### I want to use `venv`
This is supported. Use `kernel-create-venv` in place of `kernel-create` in step 3, and you will get a [**Python Virtual Environment**](https://docs.python.org/3/library/venv.html) instead.

---
*Last updated: August 2026*
