# Installing Extra Software
As part of the Research Nexus, STScI provides pre-installed software. However, you can also install your own software.

<span style="font-variant:small-caps;">Note:</span> Any commands given on this page must be entered into a terminal window. To open a new terminal window, select <span style="font-variant:small-caps;">file > new terminal</span> from the menu bar.

## What software is pre-installed?
To get a full list of pre-installed software, run `conda list`. Since this full list is quite long, you can filter it with `conda list <package>`. For example, `conda list python` or `conda list numpy`.

If there is a package that you think should be included by default, you can submit a request to the [Roman help desk](https://stsci.service-now.com/roman).

## How do I install and manage my own software?
It is essential to create software environments when working in the cloud nexus. A simple `pip install <package>` will not result in a persistent installation. Instead, it will produce a temporary installation that will be deleted upon your next log in.

As part of the Research Nexus, you can use helper commands to create and manage software environments. Follow the steps below to setup your own environments and install packages.

### 1. Creating a Conda Environment

First, use the `kernel-create` command to generate an environment for your software. You can select your desired Python version, and choose a name for the environment.

`kernel-create <environment-name> [<python-version>] [<lab-display-name>]`

Note that "environment name" is used in terminal commands, while "lab-display-name" is what appears when selecting a Notebook kernel. For example, to create a Python 3.12 environment that will appear as "WFI Lightcurves" in Jupyter:

`kernel-create wfi-lc 3.12 "WFI Lightcurves"`

Now that we've created the base environment, we can proceed to the next step.

### 2. Activating an Environment

To install software, we must first activate the environment. Note that we need to use the environment name, not the display name. Following the example above, this would be:

`source kernel-activate wfi-lc`

With the kernel activated, we can now install software.

### 3. Installing Software

Once the kernel is activated, you can use pip as usual. For example:

`pip install lightkurve`


### 4. Deleting an Environment

To remove an environment you no longer want, use the `kernel-delete` command, e.g.:

`kernel-delete wfi-lc`


### Other Notes
#### I want to use venv!
This is supported. Simply swap the command in step 1 for `kernel-create-venv`, and you'll get a [Python Virtual Environment](https://docs.python.org/3/library/venv.html) instead.
