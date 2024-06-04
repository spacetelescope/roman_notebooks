# What is the Roman Science Platform?

The Roman Science Platform uses a web-based platform, called [JupyterHub](https://docs.jupyter.org/en/latest/). It enables users to run Python Notebooks and other software remotely in a web browser without needing to install software on a local computer. Notebooks are a convenient way of packaging code, its outputs, and visualizations.

## Who is the RSP for?

This platform is for everyone interested in analyzing data from the [Roman Space Telescope](https://archive.stsci.edu/missions-and-data/roman). Frequently used Python packages are pre-installed, which enable you to analyze these data products without downloading or configuring software.

There are [tutorials](tutorials.md) available that demonstrate how to simulate, analyze, and visualize Roman data in the science platform. These Notebooks are added from the [roman_notebooks repository](https://github.com/spacetelescope/roman_notebooks), so feel free to contribute there with issues and PRs.

## Why use a science platform?
The primary advantage of working in a science platform is proximity to data. In the case of Roman's estimated 20 PB archive, it would be extremely difficult to download any fraction of these files to your local machine. RSP, by virtue of running in the same datacenter that houses the Roman data, offers quick access to all of this data, no downloads required. RSP also lowers the barrier to accessing and analyzing data by offering pre-installed Python environments that are configured for particular scientific use-cases.

## Restarting Your Server

The virtual server that runs your personal instance of RSP will shut down after ~1 hour of inactivity; you will be able to restart it the next time you access the platform.

You can start and stop your computing server any time from the JupyterHub control panel, which can be accessed from the top menu in JupyterLab (<span style="font-variant:small-caps;">file › Hub Control Panel</span>) or the "Home" tab from JupyterHub pages. You might use this to, for example, clear unwanted changes to your Python environment.

## More Information

If you are not familiar with Jupyter, Python, or the Roman Mission, you might find these resources useful:

- [RDox, the home for Roman Documentation](https://roman-docs.stsci.edu/)
- [JupyterHub Documentation](https://docs.jupyter.org/en/latest/)
- [Roman Data Archive at MAST](https://archive.stsci.edu/missions-and-data/roman)
- [Python for Everybody](https://www.py4e.com/), a free introductory Python course that covers the basics of the language.
