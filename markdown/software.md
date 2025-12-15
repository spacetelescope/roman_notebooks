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

As part of the Research Nexus, you can use helper commands to create and manage software environments. Follow the steps below to set up your own environments and install packages.

### 0. Listing Environments

To list environments, including those you have installed manually, run:

`kernel-list`

### 1. Creating a Conda Environment

Use the `kernel-create` command to generate an environment for your software. You can select your desired Python version and choose a name for the environment.

`kernel-create <environment-name> [<python-version>] [<lab-display-name>]`

The *environment name* is used in terminal commands, while *lab-display-name* is what appears when selecting a Notebook kernel.

**Example**: To create a Python 3.12 environment that will appear as “WFI Lightcurves” in Jupyter:

`kernel-create wfi-lc 3.12 "WFI Lightcurves"`

Alternatively, `<python-version>` may be replaced with a path to a YAML file. The YAML file will then be used to build the environment. See step 4 to learn how to export a YAML file from an existing environment.

Once the environment is created, proceed to the next step.

### 2. Activating an Environment

To install software, you must first activate the environment. Use the *environment name*, not the display name.

Continuing the example above, activation would be:

`source kernel-activate wfi-lc`

With the environment activated, you can install software.

### 3. Installing Software

Once an environment is activated, you may use `pip` as usual. For example:

`pip install lightkurve`

### 4. Exporting an Environment
To export an environment for later use (e.g., after modifying the default installation), use the `kernel-export` command:

`kernel-export <environment-name> <output-file-name.yaml>`

For example:

`kernel-export wfi-lc wfi-lc-specs.yaml`

To create an environment using this YAML file, replace the Python version in step 2 with a path to the YAML file.

### 5. Deleting an Environment

To remove an environment you no longer want, use:

`kernel-delete <environment-name>`

Example:

`kernel-delete wfi-lc`

### Other Notes
#### I want to use `venv`
This is supported. Use `kernel-create-venv` in place of `kernel-create` in step 1, and you will get a [**Python Virtual Environment**](https://docs.python.org/3/library/venv.html) instead.

---
*Last Updated: December 2025*
