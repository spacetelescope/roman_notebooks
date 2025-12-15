# Notebook Tutorials

Notebook Tutorials are short, self-contained examples presented as Jupyter notebooks that demonstrate a specific analysis task or tool in the Nexus environment. Each tutorial focuses on one component—such as data access, visualization, or simulation utilities—and can be run on its own or as part of a [Science Workflow](./workflows.md).

Although the current content primarily focuses on WFI imaging mode, more material on spectroscopic products will be available in future releases.

## How to Use the Notebook Tutorials
Tutorials are designed to be run interactively. Users may work through them directly or copy them into their personal or team spaces to modify and extend. Tutorials can be used independently or as components within a larger [workflow](./workflows.md).

When you finish a tutorial, close the notebook and return to the Launcher or File Browser. Stopping your server when you are done working helps avoid unnecessary compute usage.

## A Caveat: Read-Only Notebooks and Git Sync
All tutorials in the shared `notebooks/` directory are read-only. To edit or adapt a tutorial, make a copy in your personal or team directory before making changes.

The tutorials directory is synchronized with the latest reference versions when you log in. To preserve your own edits, store your working copies outside the tutorials directory—for example, in `~/nexus-user-space/` or in a team space.

## All Notebooks
Below is the current set of Notebook Tutorials available in the Nexus. Each tutorial can be run independently and may appear in one or more [Science Workflows](./workflows).

**Data Access and Exploration**

- [**Data Discovery and Access**](../content/notebooks/data_discovery_and_access/data_discovery_and_access.ipynb)

  Retrieve data from MAST or access simulated Roman data in the cloud archive ("S3 bucket").

  *Science Workflow(s)*: [WFI Data Analysis](./workflows/wfi-data-analysys.md)
  
- [**Working with ASDF**](../content/notebooks/working_with_asdf/working_with_asdf.ipynb)

  Open ASDF files with roman_datamodels, access metadata, manipulate arrays, and save changes to disk.

  *Science Workflow(s)*: [WFI Data Simulation](./workflows/wfi-data-sim.md), [WFI Data Analysis](./workflows/wfi-data-analysys.md)

- [**Data Visualization**](../content/notebooks/data_visualization/data_visualization.ipynb) 

  Visualize and explore Roman WFI images.

  *Science Workflow(s)*: [WFI Data Simulation](./workflows/wfi-data-sim.md), [WFI Data Analysis](./workflows/wfi-data-analysys.md)

**WFI Data Simulation and Calibration Pipelines**

- [**Roman I-sim**](../content/notebooks/romanisim/romanisim.ipynb)
  
  Generate Level 1 and Level 2 WFI imaging products.

  *Science Workflow(s)*: [WFI Data Simulation](./workflows/wfi-data-sim.md)

- [**Exposure Pipeline**](../content/notebooks/exposure_pipeline/exposure_pipeline.ipynb)     

  Process Level 1 data with the Roman WFI science calibration pipeline, RomanCal, to produce Level 2 exposure-level data.

  *Science Workflow(s)*: [WFI Data Simulation](./workflows/wfi-data-sim.md)
  
- [**Mosaic Pipeline**](../content/notebooks/mosaic_pipeline/mosaic_pipeline.ipynb) 

  Combine multiple Level 2 data products into a Level 3 distortion-corrected and co-added image using the Roman WFI science calibration pipeline, RomanCal.

  *Science Workflow(s)*: [WFI Data Simulation](./workflows/wfi-data-sim.md)
  
- [**WFI TVAC Bright Star Data**](../content/notebooks/ground_test_analysis/wfi_tvac_brightstar.ipynb)
   
  Process and explore WFI Bright Star Saturation Test data from the TVAC campaign using RomanCal, and visualize the resulting calibrated products.

  *Science Workflow(s)*: [WFI Data Analysis](./workflows/wfi-data-analysys.md)

**Measurements and Analysis Tools**

- [**Aperture Photometry**](../content/notebooks/aperture_photometry/aperture_photometry.ipynb) 

  Perform forced aperture photometry on a simulated WFI image.

  *Science Workflow(s)*: [WFI Data Analysis](./workflows/wfi-data-analysys.md)

- [**Galaxy Shapes**](../content/notebooks/measuring_galaxy_shapes/measuring_galaxy_shapes.ipynb)  

  Perform shape measurements of galaxies on a simulated WFI image.

  *Science Workflow(s)*: [WFI Data Analysis](./workflows/wfi-data-analysys.md)

- [**Roman Cutouts**](../content/notebooks/roman_cutouts/roman_cutouts.ipynb) 

  Generate cutouts from a Roman WFI image.

  *Science Workflow(s)*: [WFI Data Analysis](./workflows/wfi-data-analysys.md)
  
- [**Grism Spectral Extraction**](../content/notebooks/grism_spectral_extraction/grism_spectral_extraction.ipynb) 

  Extract 1-D spectra from a simulated Roman WFI 2-D slitless spectral image.

  *Science Workflow(s)*: [WFI Data Analysis](./workflows/wfi-data-analysys.md)

**Planning Utilities**
- [**Pandeia**](../content/notebooks/pandeia/pandeia.ipynb)         

  Estimate the exposure parameters needed to reach a given SNR for simulated sources in a small area of one WFI detector.

  *Science Workflow(s)*: [WFI Observations Planning](./workflows/wfi-obs-plan.md)
  
- [**RIST**](../content/notebooks/rist/rist.ipynb)

  Roman Interactive Sensitivity Tool. Simplified, interactive version of Pandeia. Estimate the SNR for a variety of target brightnesses and filters.

  *Science Workflow(s)*: [WFI Observations Planning](./workflows/wfi-obs-plan.md)
  
- [**STIPS**](../content/notebooks/stips/stips.ipynb)

  Simulate large astronomical scenes with the WFI full field-of-view.

  *Science Workflow(s)*: [WFI Observations Planning](./workflows/wfi-obs-plan.md)
  
- [**Synphot**](../content/notebooks/synphot/synphot.ipynb)

  Synthetic photometry software; estimate the brightness of sources observed with Roman WFI.

  *Science Workflow(s)*: [WFI Observations Planning](./workflows/wfi-obs-plan.md)
  
- [**STPSF**](../content/notebooks/stpsf/stpsf.ipynb)  

  Generate WFI simulated Point Spread Functions using STPSF.

  *Science Workflow(s)*: [WFI Observations Planning](./workflows/wfi-obs-plan.md)
  
- [**Footprint Visualization Tool**](../content/notebooks/footprint_visualization/footprint_visualization.ipynb)
  
  Visualize the on-sky footprint of an APT program and generate optional exposure summaries or healsparse maps using footprint utilities.

  *Science Workflow(s)*: [WFI Observations Planning](./workflows/wfi-obs-plan.md)
  
- [**Roman Background Visualization Tool (RBVT)**](../content/notebooks/background_visualization_tool/RBVT.ipynb)

  Explore and visualize time-variable Roman sky backgrounds (zodiacal, ISM, thermal) across wavelength, sky position, and calendar date to support observation planning.

  *Science Workflow(s)*: [WFI Observations Planning](./workflows/wfi-obs-plan.md)

---
*Last Updated: December 2025* 
