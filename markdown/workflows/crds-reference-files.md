# RRN Science Workflows: WFI Reference File Exploration

This science workflow introduces the Calibration Reference Data System (CRDS) reference files used to calibrate Roman Wide Field Instrument (WFI) data. It guides users through retrieving recommended files, inspecting their common structure with `roman_datamodels`, and exploring the contents of specific reference-file types.

The introductory notebook should be completed first. The remaining notebooks are standalone tutorials that users can select according to the calibration products relevant to their work.

## Workflow Overview

1. [**CRDS Reference Files**](../../notebooks/crds_reference_files/crds_reference_files.ipynb)

   Learn how CRDS matches and delivers reference files, retrieves recommendations with `crds.getrecommendations()`, and locates files with `crds.getreferences()`. The notebook also introduces CRDS mapping files and demonstrates how to download a reference file by name.

2. **Retrieve, inspect, and explore individual reference-file types**

   Choose from the tutorials below according to the calibration products relevant to your work. Each tutorial retrieves its reference file through CRDS, opens it with `roman_datamodels`, uses the `.info()` method to inspect its metadata and data structure, and then explores content specific to that reference-file type. The groups organize the tutorials by the role each file plays in calibration; they are categories for this workflow rather than official CRDS classifications.

### Foundational Reference Files

These reference files identify unusable pixels and characterize fundamental detector corrections:

| Reference File | Purpose | Notebook |
| --- | --- | --- |
| **MASK** (Bad Pixel Mask) | Identify bad pixels using data-quality flags and bitwise flag operations. | [Bad Pixel Mask](../../notebooks/crds_reference_files/bad_pixels_mask_reffile.ipynb) |
| **DARK** | Examine pixel-by-pixel and frame-by-frame dark-current values for detector readout modes. | [Dark](../../notebooks/crds_reference_files/dark_reffile.ipynb) |
| **SATURATION** | Inspect per-pixel saturation thresholds and associated data-quality flags. | [Saturation](../../notebooks/crds_reference_files/saturation_reffile.ipynb) |
| **FLAT** | Explore pixel-to-pixel sensitivity corrections across the detector. | [Flat](../../notebooks/crds_reference_files/flat_reffile.ipynb) |

### Detector Characterization

These products characterize detector response, noise, pixel area, and geometric distortion:

| Reference File | Purpose | Notebook |
| --- | --- | --- |
| **GAIN** | Inspect per-pixel gain maps used to convert data numbers (DN) to electrons. | [Gain](../../notebooks/crds_reference_files/gain_reffile.ipynb) |
| **READNOISE** | Examine per-pixel read-noise estimates. | [Read Noise](../../notebooks/crds_reference_files/readnoise_reffile.ipynb) |
| **AREA** | Explore pixel-area maps that describe pixel solid angles. | [Pixel Area](../../notebooks/crds_reference_files/area_reffile.ipynb) |
| **DISTORTION** | Evaluate the astrometric distortion model and its coordinate transformations. | [Distortion](../../notebooks/crds_reference_files/distortion_reffile.ipynb) |

### Linearity Reference Files

| Reference File | Purpose | Notebook |
| --- | --- | --- |
| **LINEARITY family** | Explore `LINEARITY`, `INVERSELINEARITY`, and `INTEGRALNONLINEARITY` products used to characterize and correct nonlinear detector response. | [Linearity](../../notebooks/crds_reference_files/linearity_reffile.ipynb) |

### Photometric Calibration

| Reference File | Purpose | Notebook |
| --- | --- | --- |
| **PHOTOM** | Inspect conversion factors used to place measured count rates into calibrated physical units. | [Photometric Calibration](../../notebooks/crds_reference_files/photom_reffile.ipynb) |

### Reference Pixel and PSF Reference Files

Explore reference-pixel correction coefficients, point-spread-function (PSF) models, and empirical point-spread-function (ePSF) data:

| Reference File | Purpose | Notebook |
| --- | --- | --- |
| **REFPIX** | Examine frequency-dependent coefficients used for reference-pixel correction. | [Reference Pixel](../../notebooks/crds_reference_files/reference_pixel_reffile.ipynb) |
| **PSF/ePSF** | Explore extended PSF models and multidimensional ePSF stamps. | [PSF/ePSF](../../notebooks/crds_reference_files/psf_reffile.ipynb) |

## Related Resources

- [**CRDS for Roman Reference Files**](https://roman-docs.stsci.edu/data-handbook-home/accessing-wfi-data/crds-for-reference-files) provides additional background on obtaining and using Roman calibration reference files.
- [**WFI Data Simulation**](./wfi-data-sim.md) uses CRDS reference files to model instrumental effects in Roman I-sim products.
- [**WFI Data Analysis**](./wfi-data-analysis.md) works with calibrated products whose accuracy depends on the applicable reference files.
- [**Exposure Pipeline**](../../notebooks/exposure_pipeline/exposure_pipeline.ipynb) demonstrates where RomanCal applies reference files while processing Level 1 data into Level 2 products.

## Caveats and Limitations

- Reference files and CRDS recommendations may change as WFI characterization and calibration mature.
- The notebooks demonstrate the reference files available for the Early Access environment and may not represent the complete set of products used during Roman science operations.
- Reference-file recommendations depend on the CRDS context and dataset metadata used for a query.

---
*Last Updated: August 2026*
