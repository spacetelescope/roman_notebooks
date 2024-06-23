# RSP Jupyter Notebooks Tutorials
Jupyter Notebooks offer an efficient and powerful way to interact with Roman datasets. Always save and shut down all notebooks, and log out of JupyterLab when you have finished your work. This is important to preserve resources for other users and to ensure you enter the RSP in a known state every time.

## How to Use the Notebook Tutorials
A set of predefined Jupyter Notebook tutorials is available to demonstrate how to use tools and software to access, simulate, process, visualize, and analyze Roman Wide Field Instrument (WFI) data within the science platform. Each tutorial is self-contained, well-documented, and guides users through each step.

Each notebook can also be seen as an individual component or module within a larger science workflow, offering users a complete end-to-end experience. While many different workflows are possible, the current documentation focuses on three main use cases: WFI observation planning, WFI data simulations, and WFI data analysis.

### Summary
- Tutorial: A notebook demonstrating how to use specific code or tools.
- Science Workflow: A combination of documentation and notebook tutorials demonstrating how to achieve a specific science-focused use case.

### Workflows
While users can choose to run any single Jupyter Notebook tutorial as a standalone tool, Science Workflows are designed to offer a complete end-to-end experience. Here, we consider three common workflows focused on the Roman Wide Field Instrument (WFI):

- [WFI Observation Planning](workflows/wfi-obs-plan.md)
- [WFI Data Simulation](workflows/wfi-data-sim.md)
- [WFI Data Analysis](workflows/wfi-data-analysis.md)

There are many potential workflows not covered in this outline; even if you don't see it here, the RSP can likely support your workflow! While the current content primarily focuses on the WFI imaging mode, Jupyter Notebook tutorials and Science Workflows for spectroscopic products will be available by Winter 2024.

## All Notebooks
Below is an outline of the content covered in each notebook and the Science Workflows they are part of. While the current content primarily focuses on the WFI imaging mode, Jupyter Notebook tutorials for spectroscopic products will be available by Winter 2024.



| Jupyter Notebook Tutorial                                                                                   | Content and Scope                                                                                                       | Science Workflow(s)                      |
|-------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|------------------------------------------|
| [Data Discovery and Access](../content/notebooks/data_discovery_and_access/data_discovery_and_access.ipynb) | Access data in the cloud archive ("S3 bucket")                                                                          | WFI Data Analysis                        |
| [Working with ASDF](../content/notebooks/working_with_asdf/working_with_asdf.ipynb)                         | Open ASDF files with roman_datamodels, access metadata, manipulate arrays, and save changes to disk                     | WFI Data Simulation<br>WFI Data Analysis |
| [Data Visualization](../content/notebooks/data_visualization/data_visualization.ipynb)                      | Use Imviz to display a preview of Roman Level 2 products.                                                               | WFI Data Simulation<br>WFI Data Analysis |
| [Roman I-sim](../content/notebooks/romanisim/romanisim.ipynb)                                               | Generate Level 1 and Level 2 WFI imaging products.                                                                      | WFI Data Simulation                      |
| [RomanCal](..content/notebooks/romancal/romancal.ipynb)                                                     | Process WFI L1 imaging raw data to obtain exposure level products.                                                      | WFI Data Simulation<br>WFI Data Analysis |
| [Aperture Photometry](../content/notebooks/aperture_photometry/aperture_photometry.ipynb)                   | Perform forced aperture photometry on a simulated WFI image.                                                            | WFI Data Analysis                        |
| [Galaxy Shapes](../content/notebooks/measuring_galaxy_shapes/measuring_galaxy_shapes.ipynb)                 | Perform shape measurements of galaxies on a simulated WFI image.                                                        | WFI Data Analysis                        |
| [Pandeia](../content/notebooks/pandeia/pandeia.ipynb)                                                       | Estimate the exposure parameters needed to reach a given SNR for simulated sources in a small area of one WFI detector. | WFI Observations Planning                |
| [RIST](../content/notebooks/rist/rist.ipynb)                                                                | Simplified, interactive version of Pandeia. Estimate the SNR for a variety of target brightnesses and filters.          | WFI Observations Planning                |
| [STIPS](../content/notebooks/stips/stips.ipynb)                                                             | Simulate large astronomical scenes with WFI full field-of-view.                                                         | WFI Observations Planning                |
| [Synphot](../content/notebooks/romanisim_romancal/romanisim_romancal.ipynb)                                 | Synthetic photometry software, estimate the brightness of sources observed with Roman WFI.                              | WFI Observations Planning                |
| [WebbPSF](../content/notebooks/webbpsf/webbpsf.ipynb)                                                       | Generate WFI simulated Point Spread Functions using WebbPSF.                                                            | WFI Observations Planning                |