# Working Locally

Running the notebook in your local machnie requires additional setting that should be run before launching this Jupyter Notebook. After creating your environment install the dependencides provided in the `requirements.txt` file within the notebook folder:

    conda create -n <env_name> python
    conda activate <env_name>
    pip install -r requirements.txt

where <env_name> is a name of your choice.

## Reference Data Installation

 If you are running this notebook locally, you will also need the `notebook_data_dependencies.py` file from the roman_notebooks repository to be in the same working directory as the notebook. This file includes a helper function `install_files()` to download and set up required reference data for packages like **STPSF**, **Pandeia**, **STIPS**, and **Synphot**.

### How it works:
- The function checks if the **environment variable** (e.g., `STSPSF_PATH`) is set **and points to an existing directory**.
- If the variable is set **and the path exists**, the data is considered **already installed** — **no download occurs**.
- If the variable is **unset or invalid**, the data will be **downloaded and extracted** to the default location.

### To avoid re-downloading:

Set up the the variable before starting the ; e.g., for `STPSF`.

In the commnad line:

    export STSPSF_PATH="/your/preferred/path/to/stpsf_data"

permanently in your shell profile (e.g., ~/.bashrc, ~/.zshrc)

or in the notebook

```os.environ['STSPSF_PATH'] = "/your/preferred/path/to/stpsf_data"```

### To force re-download:

    unset STSPSF_PATH

or in the notebook

```os.environ.pop('STSPSF_PATH', None)```

Depending on which (if any) reference data are missing, this cell may take several minutes to execute.
