# RRN Science Workflows: WFI Data Simulations

This science workflow guides users through the simulation, processing, manipulation, and visualization of Roman WFI imaging data products.

**Important**: To run this workflow, start a **medium server** in the RRN.


## Workflow Overview
- [**Roman-I-Sim**](../../notebooks/romanisim/romanisim.ipynb)

  Simulate Roman WFI raw (L1) and exposure-level (L2) products using [Roman-I-Sim](https://romanisim.readthedocs.io/en/latest/), a GalSim-based simulator for WFI imaging data. Roman I-Sim uses [Galsim](https://github.com/GalSim-developers/GalSim) to render astronomical scenes, [STPSF](https://roman-docs.stsci.edu/simulation-tools-handbook-home/stpsf-for-roman) to model the point-spread function, and [CRDS](https://roman-docs.stsci.edu/data-handbook-home/accessing-wfi-data/crds-for-reference-files) reference files to apply instrument calibration effects. Simulations can be generated from either synthetic catalogs or Gaia-based catalogs. Outputs are written in the standard [Roman ASDF format](https://roman-docs.stsci.edu/data-handbook-home/wfi-data-format/introduction-to-asdf).
  
- [**Working with ASDF**](../../notebooks/working_with_asdf/working_with_asdf.ipynb)

  Explore Roman WFI data products stored in the [Advanced Scientific Data Format (ASDF)](https://roman-docs.stsci.edu/data-handbook-home/wfi-data-format/introduction-to-asdf). This step introduces the structure of Roman WFI ASDF files, including metadata, data arrays, and provenance information, and applies to both simulated and future flight-like data products. To learn more, visit the [RDox pages on Roman WFI data levels and products](https://roman-docs.stsci.edu/data-handbook-home/wfi-data-format/data-levels-and-products).
  
- [**Exposure Pipeline**](../../notebooks/exposure_pipeline/exposure_pipeline.ipynb):
  
  Use RomanCal, the Roman calibration pipeline, to process raw (L1) data simulated with [Roman-I-Sim](https://romanisim.readthedocs.io/en/latest/) into exposure level products (L2). The exposure level pipeline contains the algorithms necessary to correct raw WFI data for instrumental effects, and
collapses the data along the time axis into rate images suitable for scientific analysis. To learn more about the overall exposure level pipeline and its different steps visit the [RDox documentation](https://roman-docs.stsci.edu/data-handbook-home/roman-stsci-data-pipelines/exposure-level-pipeline).

- [Data Visualization](../../content/notebooks/data_visualization/data_visualization.ipynb): Visualize Roman WFI Exposure Level Products
> Visualize your L2 exposure level products using Matplotlib and Imviz, a tool for visualizing and quickly analyzing 2D astronomical images. Imviz is based on the Jupyter platform and includes built-in Astropy functionality. For additional background information, consult [Imviz documentation on ReadTheDocs](https://jdaviz.readthedocs.io/en/latest/imviz/index.html).
- [Mosaic Pipeline](../../content/notebooks/mosaic_pipeline/mosaic_pipeline.ipynb): Process Roman WFI Exposure Level Products into Mosaic Images
> Use RomanCal, the Roman calibration pipeline, to process exposure level (L2) products into mosaic (L3) images. The mosaic pipeline is responsible for combining individual detector exposures into mosaics made up of multiple exposures. In this context, mosaic indicates a combination or stack of multiple exposures into a larger or deeper image. To learn more about the overall mosaic level pipeline and its different steps visit the [RDox documentation](https://roman-docs.stsci.edu/data-handbook-home/roman-stsci-data-pipelines/mosaic-level-pipeline).

  <img width="400" alt="image" src="https://github.com/user-attachments/assets/99d0bd05-b0f3-428f-8193-f9dcd27132f0" />

## Caveats and limitations
While the current content focuses on the WFI imaging mode, more content on the WFI spectroscopic mode will be available in future releases.
