# Installing Software

It is essential to create software environments when working in a cloud platform. A simple `pip install <package>` will not produce the desired installation.

As part of the science platform, you can use some helper commands to create and manage new software environments. Follow the steps below to create your own environments and install packages.

## 1. Creating a Conda Environment

First, you should use the `kernel create` command to generate an environment for your software. You can select your desired Python version, and choose a name for the environment.

`kernel-create <environment-name> [<python-version>] [<lab-display-name>]`

Note that "environment name" is used in terminal commands, while "lab-display-name" is what appears when you select a Notebook kernel. For example, to create a Python 3.12 environment that will appear as "TESS Lightcurves" in Jupyter:

`kernel-create tess-lc 3.12 "TESS Lightcurves"`

Now that we've created the base environment, we can proceed to the next step.

## 2. Activating an Environment

To install software, we must activate the environment. Note that we need to use the environment name, not the display name. Following the above example, this would be:

`kernel-activate tess-lc`

With the kernel activated, you can now install software.

## 3. Installing Software

In an activated kernel, you can use pip as you would normally. For example:

`pip install lightkurve`


## 4. Deleting an Environment

To remove an environment you no longer want, use the `kernel-delete` command, e.g.:

`kernel-delete tess-lc`


## Other Notes
### I want to use venv!
This is supported. Simply swap the command in step 1 for `kernel-create-venv`, and you'll get a [Python Virtual Environment](https://docs.python.org/3/library/venv.html) instead.