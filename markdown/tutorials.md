# Notebook Tutorials

Nexus Notebook Tutorials are short, self-contained Jupyter notebooks that demonstrate specific analysis tasks and tools in the Nexus environment. You can run each tutorial independently or use it as part of a guided [Science Workflow](./workflows.md). The current collection focuses primarily on WFI imaging, with additional spectroscopy material planned for future releases.

Complementary Roman-specific tutorials developed and maintained by the [Mikulski Archive for Space Telescopes (MAST) ](https://mast.stsci.edu/search/ui/#/roman)are listed in the Roman Tutorials from MAST section below.
## Using the Nexus Notebook Tutorials

Open a tutorial in JupyterLab and work through its cells interactively. For help with the interface, see [Working in JupyterLab](./jupyter.md).

Nexus Tutorials in the shared `notebooks/` directory are read-only and synchronized with the latest reference versions when you log in. To modify a tutorial and preserve your changes, copy it before editing to your persistent personal home directory (`/home/{your-username}/`) or a directory for a team you belong to (`/teams/{team-name}/`).

When you finish working, close the notebook and return to the Launcher or File Browser. Closing a notebook or browser does not stop your server. To avoid unnecessary compute usage, follow the instructions for [stopping your server](./server.md).

## Nexus Notebook Tutorials

### Data Access and Exploration

| Tutorial | Purpose | Science workflow(s) |
| --- | --- | --- |
| [**Data Discovery and Access**](../notebooks/data_discovery_and_access/data_discovery_and_access.ipynb) | Retrieve data from MAST or access simulated Roman data in cloud storage. | [WFI Data Analysis](./workflows/wfi-data-analysis.md) |
| [**Catalog Database Access**](../notebooks/catalog_database_access/catalog_database_access.ipynb) | Access and query Roman catalogs from MAST databases. | [Roman Data Essentials](./workflows/Intro_Workflow.md), [WFI Data Analysis](./workflows/wfi-data-analysis.md) |
| [**Working with ASDF and parquet**](../notebooks/working_with_asdf/working_with_asdf.ipynb) | Open Roman ASDF files with `roman_datamodels`, inspect metadata and arrays, save changes, and read and explore Roman catalog data in Parquet format. | [Roman Data Essentials](./workflows/Intro_Workflow.md), [WFI Data Simulation](./workflows/wfi-data-sim.md), [WFI Data Analysis](./workflows/wfi-data-analysis.md) |
| [**Data Visualization with Matplotlib**](../notebooks/data_visualization/data_visualization.ipynb) | Visualize and explore Roman WFI images with Matplotlib. | [Roman Data Essentials](./workflows/Intro_Workflow.md), [WFI Data Simulation](./workflows/wfi-data-sim.md), [WFI Data Analysis](./workflows/wfi-data-analysis.md) |
| [**Data Visualization with Jdaviz**](../notebooks/data_visualization/jdaviz_data_visualization.ipynb) | Interactively examine, navigate, and compare Roman WFI images with Jdaviz. | [Roman Data Essentials](./workflows/Intro_Workflow.md), [WFI Data Simulation](./workflows/wfi-data-sim.md), [WFI Data Analysis](./workflows/wfi-data-analysis.md) |
| [**Guiding Diagnostics Dashboard**](../notebooks/guiding_diagnostics_dashboard/guiding_diagnostics_dashboard.ipynb) | Explore Roman WFI guiding performance, including pointing jitter, noise-equivalent angles (NEAs), and guide window images. | [WFI Data Analysis](./workflows/wfi-data-analysis.md) |

### WFI Data Simulation and Calibration Pipelines

| Tutorial | Purpose | Science workflow(s) |
| --- | --- | --- |
| [**Roman I-sim**](../notebooks/romanisim/romanisim.ipynb) | Generate Level 1 and Level 2 WFI imaging products. | [WFI Data Simulation](./workflows/wfi-data-sim.md) |
| [**Exposure Pipeline**](../notebooks/exposure_pipeline/exposure_pipeline.ipynb) | Process Level 1 data with the `romancal` calibration pipeline to produce Level 2 exposure-level data. | [WFI Data Simulation](./workflows/wfi-data-sim.md) |
| [**Mosaic Pipeline**](../notebooks/mosaic_pipeline/mosaic_pipeline.ipynb) | Combine Level 2 products into a Level 3 distortion-corrected, co-added image with `romancal`. | [WFI Data Simulation](./workflows/wfi-data-sim.md) |
| [**CCS Simulations**](../notebooks/ccs_simulations/ccs_simulations.ipynb) | Explore scaled-down simulations of the High-Latitude Wide-Area Survey and Galactic Bulge Time-Domain Survey Core Community Survey programs. | [WFI Data Simulation](./workflows/wfi-data-sim.md) |
| [**CRDS Reference Files**](../notebooks/crds_reference_files/README.md) | Learn how the Calibration Reference Data System (CRDS) organizes and supplies reference files, and explore the major reference file types. | [WFI Reference File Exploration](./workflows/crds-reference-files.md) |
| [**Time Domain Simulations**](../notebooks/time_domain_simulations/time_domain_simulations.ipynb) | Simulate time-series observations of a Type Ia supernova on a static scene and create cutouts of the variable source. | [Time Domain](./workflows/time-domain.md) |
| [**WFI TVAC Bright Star Data**](../notebooks/ground_test_analysis/wfi_tvac_brightstar.ipynb) | Process and explore WFI Bright Star Saturation Test data from the thermal vacuum campaign with `romancal`. | [WFI Data Analysis](./workflows/wfi-data-analysis.md) |

### Measurements and Analysis Tools

| Tutorial | Purpose | Science workflow(s) |
| --- | --- | --- |
| [**Aperture Photometry**](../notebooks/aperture_photometry/aperture_photometry.ipynb) | Perform forced aperture photometry on a simulated WFI image. | [WFI Data Analysis](./workflows/wfi-data-analysis.md) |
| [**Galaxy Shapes**](../notebooks/measuring_galaxy_shapes/measuring_galaxy_shapes.ipynb) | Measure galaxy shapes in a simulated WFI image. | [WFI Data Analysis](./workflows/wfi-data-analysis.md) |
| [**Roman Cutouts**](../notebooks/roman_cutouts/roman_cutouts.ipynb) | Generate cutouts from a Roman WFI image. | [WFI Data Analysis](./workflows/wfi-data-analysis.md) |
| [**Time Domain Analysis**](../notebooks/time_domain_analysis/time_domain_analysis.ipynb) | Perform aperture and PSF photometry on time-series cutouts, create a light curve, and estimate properties of a Type Ia supernova. | [Time Domain](./workflows/time-domain.md) |
| [**Grism Spectral Extraction**](../notebooks/grism_spectral_extraction/grism_spectral_extraction.ipynb) | Extract one-dimensional spectra from a simulated Roman WFI two-dimensional slitless spectral image. | [WFI Data Analysis](./workflows/wfi-data-analysis.md) |

### Planning Utilities

| Tutorial | Purpose | Science workflow(s) |
| --- | --- | --- |
| [**Pandeia**](../notebooks/pandeia/pandeia.ipynb) | Estimate the exposure parameters needed to reach a given signal-to-noise ratio (S/N) for simulated sources in a small area of one WFI detector. | [WFI Observation Planning](./workflows/wfi-obs-plan.md) |
| [**RIST**](../notebooks/rist/rist.ipynb) | Estimate S/N for a range of target brightnesses and filters with the Roman Interactive Sensitivity Tool. | [WFI Observation Planning](./workflows/wfi-obs-plan.md) |
| [**STIPS**](../notebooks/stips/stips.ipynb) | Simulate large astronomical scenes across the full WFI field of view. | [WFI Observation Planning](./workflows/wfi-obs-plan.md) |
| [**Synphot**](../notebooks/synphot/synphot.ipynb) | Estimate the brightness of sources observed with Roman WFI using synthetic photometry. | [WFI Observation Planning](./workflows/wfi-obs-plan.md) |
| [**STPSF**](../notebooks/stpsf/stpsf.ipynb) | Generate simulated WFI point-spread functions with STPSF. | [WFI Observation Planning](./workflows/wfi-obs-plan.md) |
| [**Roman Target Visibility Tool (RTVT)**](../notebooks/target_visibility_tool/roman_target_visibility_tool.ipynb) | Estimate when astronomical targets are observable under Roman's Sun-angle constraints and compare visibility windows for multiple targets. | Not currently included in a Science Workflow |
| [**Footprint Visualization Tool**](../notebooks/footprint_visualization/footprint_visualization.ipynb) | Explore survey and observing-program footprints, determine whether coordinates fall within them, and generate exposure summaries or healsparse maps. | [Roman Data Essentials](./workflows/Intro_Workflow.md), [WFI Observation Planning](./workflows/wfi-obs-plan.md) |
| [**Roman Background Visualization Tool (RBVT)**](../notebooks/background_visualization_tool/RBVT.ipynb) | Explore time-variable Roman sky backgrounds across wavelength, sky position, and date to support observation planning. | [WFI Observation Planning](./workflows/wfi-obs-plan.md) |

## **MAST Roman Tutorials**
[MAST](https://mast.stsci.edu/search/ui/#/roman) maintains its own collection of notebook tutorials across multiple missions. The Roman-specific tutorials listed below complement the Nexus tutorials and provide additional guidance on accessing Roman science data, ground test data, and engineering telemetry through MAST.

| Tutorial | Purpose | Resources |
| --- | --- | --- |
| **MAST Metadata Search** | Search for Roman science data in MAST using metadata from science data products. | [Notebook](https://github.com/spacetelescope/mast_notebooks/blob/roman-prelaunch/notebooks/Roman/MAST_metadata_search/MAST_metadata_search.ipynb) |
| **Engineering Database Retrieval** | Retrieve Roman engineering telemetry mnemonics from the MAST Roman Engineering Database. | [Notebook](https://github.com/spacetelescope/mast_notebooks/blob/roman-prelaunch/notebooks/Roman/Engineering_Database_Retrieval/EDB_Retrieval.ipynb) |
| **CaSSI RITA Retrieval** | Retrieve Roman Integration & Test Archive (RITA) ground test data through the MAST Calibration and Supplemental Search Interface (CaSSI). | [Notebook](https://github.com/spacetelescope/mast_notebooks/blob/roman-prelaunch/notebooks/Roman/CaSSI_RITA_Retrieval/CaSSI_RITA_Retrieval.ipynb) |
| **CaSSI Supplementary Telemetry Retrieval** | Retrieve supplemental Roman telemetry, including Level 0 WFI and CGI data and calibrated engineering telemetry files, through CaSSI. | [Notebook](https://github.com/spacetelescope/mast_notebooks/blob/roman-prelaunch/notebooks/Roman/CaSSI_Supplementary_Telemetry_Retrieval/CaSSI_SuppTelem_Retrieval.ipynb) |

---
*Last updated: November 2026*
