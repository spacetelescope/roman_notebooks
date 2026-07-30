# Installing Extra Software
As part of the Research Nexus, STScI provides some pre-installed software. However, you can also install your own software.

**Note:** Any commands shown on this page must be entered into a terminal window. To open a new terminal window, select **File → New Terminal** from the JupyterLab menu bar.

## What software is pre-installed?
To view a full list of pre-installed software, run:

`conda list`

Since this list is lengthy, you can check the version of a specific package using:

`conda list <package>`

For example: 

`conda list astropy`
`conda list numpy`

If you believe a package should be included by default, you can submit a request to the [Roman Help Desk](https://stsci.service-now.com/roman).

## How do I install and manage my own software?
When working in the Nexus, it is essential to create dedicated software environments. Running:
`pip install <package>` 

inside the default environment will not create a persistent installation; it will instead create a temporary environment that is deleted when you next log in.

As part of the Roman Research Nexus (RRN), you can use helper commands to create and manage software environments. Follow the steps below to set up your own environments and install packages.


### 1. Listing Environments

To list environments, including those you have installed manually, run:

`kernel-list`

### 2. Making a requirments.txt file
Creating an environment specification (requirements.txt) file is recommended wehen setting up a new computing environment on the RRN.

The [Conda documentation](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#exporting-environments-with-conda-export) on exporting environments for sharing purposes gives a simple example of a requirements txt file. We show bellow an example of a `requirements.txt` file

```
   romancal>=1.0.1
   roman_datamodels>=1.0.0
   rad>=1.0.0
   git+https://github.com/astropy/astroquery.git@refs/pull/3593/head
   fsspec[s3]
   matplotlib
```

In the example specification above, there are several important things to note:
- Operators (e.g., >, >=, ==, <, and <=) can be used to specify package versions. Generally, packages should be specified as flexibly as possible to allow the package solver to find a solution and avoid dependency collisions. If you know you must have exactly a specific version of a package, then use the double equals sign (==) operator. If you do not specify an operator, the most recent package version possible, after accounting for dependencies and other requirements, will be used.
- One package (`astroquery`) is specified using the command. In this example, this will install the version of `astroquery` from a [GitHub pull request](https://github.com/astropy/astroquery/pull/3593)
(installing from the pull request is necessary to access Roman data via S3 until this change is merged and released). More pull request information on installing via `git` is available in the [pip documentation](https://pip.pypa.io/en/stable/topics/vcs-support/)
- The `fsspec` package is specified using `[s3]`. This defines extra instructions from the package maintainer. Not all packages have extras like this, but some do (e.g., `dask[complete]`). Check the documentation for the package if there are extras you need to specify, but in most casesd you will already be aware of these. Use of the `[s3]` option with `fsspec` installs additional tools for working with AWS S3 buckets.

### 3. Creating a Conda Environment

**!NOTE!**
*Installing new environments on the Nexus may take up to 20 minutes to complete. Updating packages within an existing environment is much faster.*

Use the `kernel-create` command to generate an environment for your software. You can select your desired Python version and choose a name for the environment.

`kernel-create <environment-name> [<python-version>] [<lab-display-name>]`

The *environment name* is used in terminal commands, while *lab-display-name* is what appears when selecting a Notebook kernel.

**Example**: To create a Python 3.12 environment that will appear as “WFI Lightcurves” in Jupyter:

`kernel-create wfi-lc 3.12 "WFI Lightcurves"`

Alternatively, `<python-version>` may be replaced with a path to a YAML file. The YAML file will then be used to build the environment. In this case the command would be:

`kernel-create wfi-lc ./environment.yml "WFI Lightcurves"`

In the enviroment file you will add python version. Here an example:

```
   name: wfi-lc   # optional
   channels:
       - conda-forge
   dependencies:
       - python=3.13
```
If using a YAML file we recommend to add `pip`, `ipython`, `ipykernel`, and `uv` to the `dependencies`. This will look as follows:

```
   name: wfi-lc
   channels:
       - conda-forge
   dependencies:
       - python=3.13
       - pip
       - ipykernel    # needed for a proper Jupyter kernel    
       - ipython              
       - uv      
```
These packages and their use are described in step 5 bellow. 

Once the environment is created, proceed to the next step.

### 4. Activating an Environment

To install software, you must first activate the environment. Use the *environment name*, not the display name.

Continuing the example above, activation would be:

`source kernel-activate wfi-lc`

With the environment activated, you can install software.

### 5. Install base tools

If not already installed with the `environment.yml` file, then first install three tools needed for package managment and supporty interactive Python session. The command:

`conda install --yes pip ipython uv`

These packages will be used later:
- pip for package management
- ipython for interactive Python sessions
- uv a extremely fast, `Rust`-based package management tool for use together with `pip`. 

Installation of `uv` is optional and can be skipped. The argument `--yes` answers any prompts with "yes" and removes the need for user interaction with the  installation process.

### 6. Installing Software

Once an environment is activated, you can install your packages included in your `requirements.txt` with file with:

`uv pip install -r requirements.txt ` 

if using `uv`, or 

`pip install -r requirements.txt`
 
 if using the usual `pip`. Make sure that the `requirements.txt` file is in the current working directory.
 
 You can also install individual packages using simple `pip` as usual. For example:

`pip install lightkurve`

See step 8 to learn how to export a YAML file from an existing environment.

### 7. Switching to a Different Environment

Similar to the code block above, you can activate another defined environment using the `kernel source-activate` command and inputting the name of the environment. For example, upon logging into the Nexus, you may be in a different environment such as `roman_cal`. To instead activate the `wfi-lc` environment, use the following command:

`source kernel-activate wfi-lc1`

When using Jupyter notebooks, all kernels you have defined will be available regardless of the command line environment.

### 8. Exporting an Environment
To export an environment for later use (e.g., after modifying the default installation), use the `kernel-export` command:

`kernel-export <environment-name> <output-file-name.yaml>`

For example:

`kernel-export wfi-lc wfi-lc-specs.yaml`

To create an environment using this YAML file, replace the Python version in step 2 with a path to the YAML file.

### 9. Deleting an Environment

To remove an environment you no longer want, use:

`kernel-delete <environment-name>`

Example:

`kernel-delete wfi-lc`

### Other Notes
#### I want to use `venv`
This is supported. Use `kernel-create-venv` in place of `kernel-create` in step 1, and you will get a [**Python Virtual Environment**](https://docs.python.org/3/library/venv.html) instead.

---
*Last Updated: Jul 29, 2026*
