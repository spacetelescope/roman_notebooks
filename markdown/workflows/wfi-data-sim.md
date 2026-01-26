# RRN Science Workflows: WFI Data Simulations

This science workflow guides users through the simulation, processing, manipulation, and visualization of Roman WFI imaging data products.

**Important**: To run this workflow, start a **medium server** in the RRN.


## Workflow Overview
- [**Roman-I-Sim**](../../notebooks/romanisim/romanisim.ipynb)

  Simulate Roman WFI raw (L1) and exposure-level (L2) products using [Roman-I-Sim](https://romanisim.readthedocs.io/en/latest/), a GalSim-based simulator for WFI imaging data. Roman I-Sim uses [Galsim](https://github.com/GalSim-developers/GalSim) to render astronomical scenes, [STPSF](https://roman-docs.stsci.edu/simulation-tools-handbook-home/stpsf-for-roman) to model the point-spread function, and [CRDS](https://roman-docs.stsci.edu/data-handbook-home/accessing-wfi-data/crds-for-reference-files) reference files to apply instrument calibration effects. Simulations can be generated from either synthetic catalogs or Gaia-based catalogs. Outputs are written in the standard [Roman ASDF format](https://roman-docs.stsci.edu/data-handbook-home/wfi-data-format/introduction-to-asdf).
  
- [**Working with ASDF**](../../notebooks/working_with_asdf/working_with_asdf.ipynb)

  Explore Roman WFI data products stored in the [Advanced Scientific Data Format (ASDF)](https://roman-docs.stsci.edu/data-handbook-home/wfi-data-format/introduction-to-asdf). This step introduces the structure of Roman WFI ASDF files, including metadata, data arrays, and provenance information, and applies to both simulated and future flight-like data products. To learn more, visit the [RDox pages on Roman WFI data levels and products](https://roman-docs.stsci.edu/data-handbook-home/wfi-data-format/data-levels-and-products).
  
- [**Exposure Pipeline**](../../notebooks/exposure_pipeline/exposure_pipeline.ipynb)
  
  Process Roman WFI raw (L1) data into exposure-level (L2) products using RomanCal, the Roman science calibration pipeline. This stage corrects instrumental effects and collapses ramp data into rate images suitable for scientific analysis. To learn more about the overall exposure level pipeline visit the [RDox documentation]([https://roman-docs.stsci.edu/data-handbook-home/roman-stsci-data-pipelines/exposure-level-pipeline](https://roman-docs.stsci.edu/data-handbook-home/roman-data-pipelines/exposure-level-pipeline)).
 
- [**Data Visualization**](../../notebooks/data_visualization/data_visualization.ipynb)

  Visualize Roman WFI exposure-level products using Matplotlib and Imviz. This step focuses on quick-look inspection and basic analysis of calibrated L2 images. Imviz is based on the Jupyter platform and includes built-in Astropy functionality. For additional background information, consult [Imviz documentation on ReadTheDocs](https://jdaviz.readthedocs.io/en/latest/imviz/index.html).

- [**Mosaic Pipeline**](../../notebooks/mosaic_pipeline/mosaic_pipeline.ipynb)

  Combine multiple exposure-level (L2) products into mosaic-level (L3) images using RomanCal. The mosaic pipeline aligns, distortion-corrects, and coadds individual detector exposures to produce deeper, wide-field images. To learn more about the overall mosaic level pipeline visit the [RDox documentation](https://roman-docs.stsci.edu/data-handbook-home/roman-data-pipelines/mosaic-level-pipeline).

<img src="https://raw.githubusercontent.com/spacetelescope/roman_notebooks/refs/heads/main/images/wfi-data-sim.jpg" alt="WFI Data Analysis Workflow" width="250" />

## Caveats and limitations
Caveats and Limitations
- This workflow focuses primarily on **WFI imaging simulations**.
- The fidelity of simulated products depends on the calibration reference files available at the time of simulation.
- Processing steps and outputs may evolve as Roman calibration software and reference data mature.

---
*Last Updated: December 2025*
 
