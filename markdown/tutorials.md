# All Notebook Tutorials
## What are Notebook Tutorials?
In the Roman Science Platform (RSP) framework, a notebook tutorial refers to a Jupyter notebook demonstrating how to use a specific piece of code or tool.  A set of predefined Jupyter notebook tutorials is available to demonstrate how to use tools and software for accessing, simulating, processing, visualizing, and analyzing Roman Wide Field Instrument (WFI) data within the science platform. Although the current content primarily focuses on WFI imaging mode, Jupyter notebook tutorials for spectroscopic products will be available by Winter 2024.

Each tutorial is self-contained, well-documented, and guides users through every step. While Jupyter notebook tutorials can be used as standalone tools, they also function as individual components or modules within larger science workflows, offering users a complete end-to-end experience.


## How to Use the Notebook Tutorials
Jupyter notebooks provide an efficient and powerful way to interact with Roman datasets. Always remember to [save and shut down all notebooks and log out](./jupyter.md) of JupyterLab when you finish your work. This is important to preserve resources for other users and to ensure that you enter the Roman Science Platform (RSP) in a known state every time.

## All Notebooks
Below is an outline of the content covered in each notebook and the Science Workflows they are part of. While the current content primarily focuses on the WFI imaging mode, Jupyter notebook tutorials for spectroscopic products will be available by Winter 2024.



| Jupyter Notebook Tutorial                                                                                   | Content and Scope                                                                                                       | Science Workflow(s)                      |
|-------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|------------------------------------------|
| [Data Discovery and Access](../content/notebooks/data_discovery_and_access/data_discovery_and_access.ipynb) | Retrieve data from MAST or access simulated Roman data in the cloud archive ("S3 bucket").                                                                          | WFI Data Analysis                        |
| [Working with ASDF](../content/notebooks/working_with_asdf/working_with_asdf.ipynb)                         | Open ASDF files with roman_datamodels, access metadata, manipulate arrays, and save changes to disk.                     | WFI Data Simulation<br>WFI Data Analysis |
| [Data Visualization](../content/notebooks/data_visualization/data_visualization.ipynb)                      | Use Imviz to display a preview of Roman Level 2 products and run quick analysis tools.                                                               | WFI Data Simulation<br>WFI Data Analysis |
| [Roman I-sim](../content/notebooks/romanisim/romanisim.ipynb)                                               | Generate Level 1 and Level 2 WFI imaging products.                                                                      | WFI Data Simulation                      |
| [RomanCal](../content/notebooks/romancal/romancal.ipynb)                                                     | Process WFI L1 imaging raw data to obtain exposure level products.                                                      | WFI Data Simulation<br>WFI Data Analysis |
| [Aperture Photometry](../content/notebooks/aperture_photometry/aperture_photometry.ipynb)                   | Perform forced aperture photometry on a simulated WFI image.                                                            | WFI Data Analysis                        |
| [Galaxy Shapes](../content/notebooks/measuring_galaxy_shapes/measuring_galaxy_shapes.ipynb)                 | Perform shape measurements of galaxies on a simulated WFI image.                                                        | WFI Data Analysis                        |
| [Pandeia](../content/notebooks/pandeia/pandeia.ipynb)                                                       | Estimate the exposure parameters needed to reach a given SNR for simulated sources in a small area of one WFI detector. | WFI Observations Planning                |
| [RIST](../content/notebooks/rist/rist.ipynb)                                                                | Roman Interactive Sensitivity Tool. Simplified, interactive version of Pandeia. Estimate the SNR for a variety of target brightnesses and filters.          | WFI Observations Planning                |
| [STIPS](../content/notebooks/stips/stips.ipynb)                                                             | Simulate large astronomical scenes with WFI full field-of-view.                                                         | WFI Observations Planning                |
| [Synphot](../content/notebooks/synphot/synphot.ipynb)                                 | Synthetic photometry software, estimate the brightness of sources observed with Roman WFI.                              | WFI Observations Planning                |
| [WebbPSF](../content/notebooks/webbpsf/webbpsf.ipynb)                                                       | Generate WFI simulated Point Spread Functions using WebbPSF.                                                            | WFI Observations Planning                |