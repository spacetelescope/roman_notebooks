# Installing Extra Software
As part of the Research Nexus, STScI provides pre-installed software. However, you can also install your own software.

<span style="font-variant:small-caps;">Note:</span> Any commands given on this page must be entered into a terminal window. To open a new terminal window, select <span style="font-variant:small-caps;">file > new terminal</span> from the menu bar.

## What software is pre-installed?
To view a full list of pre-installed software, run `conda list`. Since the list is quite long, you can check the version of a specific package by running `conda list <package>`. For example, `conda list astropy` or `conda list numpy`.

If there is a package you believe should be included by default, you can submit a request to the [Roman help desk](https://stsci.service-now.com/roman).

## How do I install and manage my own software?
When working in the Nexus, it is essential to create dedicated software environments. A simple `pip install <package>` will not result in a persistent installation. Instead, it creates a temporary installation that will be deleted the next time you log in.

As part of the Research Nexus, you can use helper commands to create and manage software environments. Follow the steps below to setup your own environments and install packages.

### 0. Listing Environments

To list environments, including those you've installed manually, run `kernel-list`.

### 1. Creating a Conda Environment

First, use the `kernel-create` command to generate an environment for your software. You can select your desired Python version, and choose a name for the environment.

`kernel-create <environment-name> [<python-version>] [<lab-display-name>]`

Note that "environment name" is used in terminal commands, while "lab-display-name" is what appears when selecting a Notebook kernel. For example, to create a Python 3.12 environment that will appear as "WFI Lightcurves" in Jupyter:

`kernel-create wfi-lc 3.12 "WFI Lightcurves"`

Alternatively, `[python-version]` can be replaced with the path to a YAML file. The YAML file will then be used to build the environment. See step 4 to learn how to export a YAML file from an existing environment.

Now that we've created the base environment, we can proceed to the next step.

### 2. Activating an Environment

To install software, we must first activate the environment. Note that we need to use the environment name, not the display name. Following the example above, this would be:

`source kernel-activate wfi-lc`

With the kernel activated, we can now install software.

### 3. Installing Software

Once the kernel is activated, you can use pip as usual. For example:

`pip install lightkurve`

### 4. Exporting an Environment
To export an environment for later use (e.g. modifying the default installation), use the `kernel-export` command:

`kernel-export <environment-name> <output-file-name.yaml>`

Following our running example, a valid command would be:

`kernel-export wfi-lc wfi-lc-specs.yaml`

To create an environment using this yaml file, replace the python version in step 2 with a path to the yaml file.


### 5. Deleting an Environment

To remove an environment you no longer want, use the `kernel-delete` command, e.g.:

`kernel-delete wfi-lc`


### Other Notes
#### I want to use venv!
This is supported. Simply swap the command in step 1 for `kernel-create-venv`, and you'll get a [Python Virtual Environment](https://docs.python.org/3/library/venv.html) instead.
