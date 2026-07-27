# CRDS Reference Files

This science workflow guides users through understanding the structure, content, and
usage of Calibration Reference Data System (CRDS) reference files for the Roman Wide
Field Instrument (WFI).

The notebooks in this workflow are designed as standalone tutorials but can
be followed sequentially for a complete introduction to how reference files are
retrieved, inspected, and visualized.

## Workflow Overview

### General CRDS Introduction

- [crds_reference_files.ipynb](../../notebooks/crds_reference_files/crds_reference_files.ipynb)

   - Learn what CRDS is, how reference files are matched and delivered, and how to use `crds.getreferences()` and `crds.getrecommendations()`.

### Reference File Inspection Fundamentals

- [crds_reference_files.ipynb](../../crds_reference_files/crds_reference_files.ipynb) (first part) + individual reference file notebooks

Understand the common structure of Roman reference files using `roman_datamodels` and the `.info()` method.

### Individual Reference File Notebooks

Explore each major reference file type in detail:

| Reference File | Purpose | Key Concepts Covered | Notebook |
|----------------|---------|----------------------|----------|
| **MASK** (Bad Pixel Mask) | DQ flags and bad pixel identification | `dq` array, bitwise flags, flagged pixel statistics | [bad_pixels_mask_reffile.ipynb](../../notebooks/crds_reference_files/bad_pixels_mask_reffile.ipynb) |
| **DARK** | Dark current correction | Pixel-by-pixel and frame-by-frame dark current values per detector readout mode | [dark_reffile.ipynb](../../notebooks/crds_reference_files/dark_reffile.ipynb) |
| **SATURATION** | Saturation thresholds | Per-pixel thresholds, flag handling | [saturation_reffile.ipynb](../../notebooks/crds_reference_files/saturation_reffile.ipynb) |
| **REFPIX** | Reference pixel correction | Frequency-dependent coefficients (`alpha`, `gamma`, `zeta`) | [reference_pixel_reffile.ipynb](../../notebooks/crds_reference_files/reference_pixel_reffile.ipynb) |
| **DISTORTION** | Astrometric distortion model | Astropy `CompoundModel`, grid evaluation, vector fields | [distortion_reffile.ipynb](../../notebooks/crds_reference_files/distortion_reffile.ipynb) |
| **PHOTOM** | Photometric calibration | conversion factors for putting pixel values into physical units | [photom_reffile.ipynb](../../notebooks/crds_reference_files/photom_reffile.ipynb) |
| **GAIN** | DN to electrons conversion | Per-pixel gain maps, amplifier structure | [gain_reffile.ipynb](../../notebooks/crds_reference_files/gain_reffile.ipynb) |
| **READNOISE** | Read noise characterization | Per-pixel read noise maps | [readnoise_reffile.ipynb](../../notebooks/crds_reference_files/readnoise_reffile.ipynb) |
| **AREA** | Pixel solid angle | Pixel area maps in steradians | [area_reffile.ipyn](../../notebooks/crds_reference_files/area_reffile.ipynb) |
| **PSF / ePSF** | Empirical point spread function | Multi-dimensional ePSF stamps, extended PSF | [psf_reffile.ipynb](../../notebooks/crds_reference_files/psf_reffile.ipynb) |
| **LINEARITY** family | Non-linearity correction | `LINEARITY`, `INVERSELINEARITY`, `INTEGRALNONLINEARITY` (per-amplifier lookup tables) | [linearity_reffile.ipynb](../../notebooks/crds_reference_files/linearity_reffile.ipynb) |


## Suggested Learning Path

1. Start with the general **CRDS Reference Files** notebook.
3. Go through the individual reference file notebooks in roughly this order:
   - MASK -> DARK -> SATURATION -> FLAT (foundational)
   - GAIN -> READNOISE -> AREA -> DISTORTION (detector characterization)
   - LINEARITY family (important for flux accuracy)
   - PHOTO (photometric calibration)
   - REFPIX, PSF/ePSF (more specialized)
4. Return to the general CRDS notebook as needed for context.


<img src="https://raw.githubusercontent.com/spacetelescope/roman_notebooks/refs/heads/main/images/crds_workflow.jpg" alt="CRDS Workflow" width="250" />


## How to Use This Workflow

- Work through the notebooks sequentially for a comprehensive understanding.
- Use individual notebooks independently when you need to inspect a specific reference file.
- All notebooks follow a consistent structure

## Related Workflows

- **WFI Data Simulation** — Uses many of these reference files via Roman-I-Sim and CRDS.
- **WFI Data Analysis** — Uses calibrated data products that depend on these reference files.
- **Exposure Pipeline** tutorial — Shows where these reference files are actually applied in `romancal`.

