# Nancy Grace Roman Space Telescope Notebooks

The `roman_notebooks` repository contains several workflows and tutorials that demonstrate how to plan observations for, simulate images from, and access and analyze data from the [Nancy Grace Roman Space Telescope](https://roman.gsfc.nasa.gov/) (Roman). Python Jupyter notebooks provide [**Tutorials**](markdown/tutorials.md) on specific topics (e.g., how to run the science data pipeline to calibrate an exposure), while [**Science Workflows**](markdown/workflows.md) combine multiple tutorials, along with documentation, to provide a guided end-to-end experience for a specific science use case.

The notebooks in this repository are designed for the [Roman Research Nexus](https://roman.science.stsci.edu), a cloud-based science platform specifically designed for Roman users. With a [MyST](https://proper.stsci.edu/proper/authentication/auth) account, users will be able to access the Nexus and learn how to work with Roman data in the cloud. The Nexus is currently under development and has limited user access, with public access planned for late 2025.

## Repository Organization

Notebook tutorials are organized under the `content/notebooks/` directory. Each notebook is contained within a folder along with a `requirements.txt` file and any other supporting files required to run the notebook.

Markdown documentation files are contained within the `markdown/` folder.

## Local Installation (Not Recommended)

The notebooks in this repository are designed to work on the Roman Research Nexus for the best user experience. Due to the size of Roman data, local use is not recommended for most users. However, we provide instructions for local installation below.

The notebooks contained in this repository can be run locally with the correct environment setup. It is recommended to create a new environment (e.g., with [mamba](https://mamba.readthedocs.io/en/latest/index.html)) to run the tutorials. For example:
```
mamba create -n roman-notebooks python ipython jupyterlab
```

Each notebook folder includes a `requirements.txt` file with the necessary Python package versions listed. To install package dependencies from a `requirements.txt` file with `pip`, first navigate to a notebook folder and then use the following command:
```
pip install -r requirements.txt
```

Several notebooks use packages that require supplementary data to be installed (e.g., `stpsf` for generating Roman Wide Field Instrument point spread functions). In those instances, a Python script is called at the beginning of the notebook to check for these data dependencies, download the appropriate data files if they are not found, and instruct you on how to set the correct environment variables.

Additionally, a correctly configured [Calibration Reference Data System](https://roman-crds.stsci.edu/static/users_guide/index.html) setup is required to simulate and/or calibrate Roman observations. Please set the environment variable below:
```
export CRDS_SERVER_URL = "https://roman-crds.stsci.edu"
export CRDS_PATH = "/path/to/crds/cache/"
```
where `CRDS_PATH` points to your CRDS cache. If you do not have a cache already, the directory will be created the first time CRDS is used in the notebooks, but the path must still be set in advance.

Note that any embedded, relative links to markdown files and other notebook tutorials may not work if the repository is cloned and modified or if files are selectively installed.

## Get Support

Please refer to the [Roman Documentation (RDox)](https://roman-docs.stsci.edu) website for technical documentation about the Roman Space Telescope.

If you need assistance, please submit a ticket through the [Roman Help Desk](https://romanhelp.stsci.edu) portal. Once logged into the help desk, click on "Get Help with the Roman Space Telescope" and then select the "Roman Research Nexus" category and submit your ticket.
