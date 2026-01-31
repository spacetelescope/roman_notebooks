# Working Locally

Running some notebooks in your local machine require additional settings that should be run before launching the Jupyter Notebook.
Some of these apply to all notebooks will other to a selected few.

## Setting up the environment for all notebooks

The notebooks were tested with Python 3.13, earlier and later versions might not have the desired results. Also note, not every notebook in this repository uses the same dependencies. For reproducibility and to avoid conflicts, each notebook folder contains its own requirements.txt file listing only the packages required for that specific notebook. 

The recommended steps:

Create a dedicated environment for the notebook you want to run:

    conda create -n <env_name> python=3.13 ipython jupyterlab
    conda activate <env_name>

where <env_name> is a name of your choice.

Navigate to the specific notebook folder and install the exact dependencies for that notebook:

    pip install -r requirements.txt

## Reference Data Installation

### To calibrate Roman observations

Additionally, a correctly configured [Calibration Reference Data System](https://roman-crds.stsci.edu/static/users_guide/index.html) setup is required to simulate and/or calibrate Roman observations. Please set the environment variable below:

```
export CRDS_SERVER_URL="https://roman-crds.stsci.edu"
export CRDS_PATH="/path/to/crds/cache/"
```

where `CRDS_PATH` points to your CRDS cache. If you do not have a cache already, the directory will be created the first time CRDS is used in the notebooks, but the path must still be set in advance.

## For simulations, analysis, and planning tools

 Some notebooks use packages like **STPSF**, **Pandeia**, **STIPS**, and **Synphot** requiring data files that are distributed separately and that are expected to follow a certain directory structure under the root directory. 

 For convenience, we have included the script `notebook_data_dependencies.py` which does this for you. The script is located in the directory *repo-root/shared/*. You can copy this script to your notebook folder or leave it in the *repo-root/shared/* directory.

### How it works:

The script includes the `install_files()` function:

- The function checks if the **environment variable** (e.g., `STSPSF_PATH`) is set **and points to an existing directory**.
- If the variable is set **and the path exists**, the data is considered **already installed** — **no download occurs**.
- If the variable is **unset or invalid**, the data will be **downloaded and extracted** to the default location.

### To avoid re-downloading:

If you already have the data locally and don't want to re-dowload it, ensure you have set up the environment variables before starting the notebook.

For example, for `STPSF` you need to define `STSPSF_PATH`.

In the commnad line or permanently in your shell profile (e.g., ~/.bashrc, ~/.zshrc):

```
export STSPSF_PATH="/your/preferred/path/to/stpsf_data"
```

You can also add a cell in your notebook with the following code:

```
os.environ['STSPSF_PATH'] = "/your/preferred/path/to/stpsf_data"
```

this cell should be run before the first code cell in the notebook. This is in particular useful with you re-run your notebook and you did not set this environment variable in your shell profile.

The other variables you might need to set are:

- `pandeia_refdata` and `PSF_DIR` when using `pandeia`
- `PYSYN_CDBS` when using `synphot`
- `stips_data` when using `stips`

### To force re-download:

If you wish to re-download the data files, even after setting the environment variable, you can accomplish this in the command line with:

```
unset STSPSF_PATH
```

for the `STSPSF_PATH` environment variable. Or in the notebook:

```
os.environ.pop('STSPSF_PATH', None)
```

Depending on which (if any) reference data are missing, this cell may take several minutes to execute.
