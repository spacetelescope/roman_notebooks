# What is the Roman Science Platform?

The Roman Science Platform (RSP) is a set of services and tools to query, visualize, simulate, and analyze Roman data. The RSP operates on a web-based platform called [JupyterHub](https://docs.jupyter.org/en/latest/), allowing users to collaboratively work in [JupyterLab](https://jupyterlab.readthedocs.io/en/latest/) sessions. Here, they can create [Jupyter notebooks](https://docs.jupyter.org/en/latest/). As web-based platform, RSP is operating-system agnostic and can be run on any modern internet browser. A stable Python environment is provided and maintained, including many commonly-used packages, the [Roman STScI Data Pipelines](https://roman-docs.stsci.edu/data-handbook-home/roman-stsci-data-pipelines), and [Roman related simulation and analysis tools](https://roman-docs.stsci.edu/simulation-tools-handbook-home). Users can create their own environments (Python or otherwise) and [install custom software](software.md). 

## Why use a science platform?
The primary advantage of working in a science platform is proximity to data. In the case of Roman's estimated 30 PB archive, it would be extremely difficult to download any fraction of these files to your local machine. RSP, running in the same data center that houses the Roman data, offers quick access to all of this data: no downloads required. RSP also lowers the barrier to accessing and analyzing data by offering pre-installed Python environments that are configured for particular scientific use-cases. By combining this pre-packaged software installation with fast access to data and the convenience of the JupyterLab environment, users can write Jupyter Notebooks that integrate code, analysis results, data visualizations, and most other existing Python functionality available for astronomical images and catalogs.

## Who is the RSP for?

The RSP is intended for users interested in preparing observing programs and/or working with data from the [Roman Space Telescope](https://archive.stsci.edu/missions-and-data/roman). We offer a variety of [Jupyter notebook tutorials](tutorials.md) that demonstrate how to use tools and software to simulate, process, visualize, and analyze Roman Wide Field Instrument (WFI) data. Additionally, we organize the tutorials into Science Workflows that showcase how to use them as building blocks to address more complex scientific use cases. 

## Restarting Your Server

The virtual server that runs your personal instance of RSP will shut down after ~1 hour of inactivity; you can restart it the next time you access the platform.

You can start and stop your computing server any time from the JupyterHub control panel, which can be accessed from the top menu in JupyterLab (<span style="font-variant:small-caps;">file › Hub Control Panel</span>) or the "Home" tab from JupyterHub pages. You might use this to, for example, clear unwanted changes to your Python environment. Shutting down after you've finished work also helps save STScI resources!

## More Information

If you are not familiar with Jupyter, Python, or the Roman Mission, you might find these resources useful:

- [RDox, the home for Roman Documentation](https://roman-docs.stsci.edu/)
- [JupyterHub Documentation](https://docs.jupyter.org/en/latest/)
- [Roman Data Archive at MAST](https://archive.stsci.edu/missions-and-data/roman)
- [Python for Everybody](https://www.py4e.com/), a free introductory Python course that covers the basics of the language.
