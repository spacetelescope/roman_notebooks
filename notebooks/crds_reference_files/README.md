# CRDS Reference Files

This directory contains a collection of notebooks that guide users through the
structure, content, and usage of Calibration Reference Data System (CRDS)
reference files for the Roman Wide Field Instrument (WFI).

The notebooks are designed as standalone tutorials but can be followed
sequentially for a complete introduction to how reference files are retrieved,
inspected, and visualized.

The [CRDS reference files overview](crds_reference_files.ipynb) explains what
CRDS is, how reference files are matched and delivered, and how to use
`crds.getreferences()` and `crds.getrecommendations()`.

## Individual Reference File Notebooks

These notebooks cover most of the reference files used by the Roman
Calibration Pipeline:

| Reference type | Purpose | Notebook |
| --- | --- | --- |
| **MASK** (Bad Pixel Mask) | Bad-pixel identification and data-quality flags | [bad_pixels_mask_reffile.ipynb](bad_pixels_mask_reffile.ipynb) |
| **DARK** | Dark-current correction | [dark_reffile.ipynb](dark_reffile.ipynb) |
| **SATURATION** | Per-pixel saturation thresholds | [saturation_reffile.ipynb](saturation_reffile.ipynb) |
| **FLAT** | Pixel-to-pixel sensitivity correction | [flat_reffile.ipynb](flat_reffile.ipynb) |
| **REFPIX** | Reference-pixel correction | [reference_pixel_reffile.ipynb](reference_pixel_reffile.ipynb) |
| **DISTORTION** | Astrometric-distortion modeling | [distortion_reffile.ipynb](distortion_reffile.ipynb) |
| **PHOTOM** | Photometric calibration | [photom_reffile.ipynb](photom_reffile.ipynb) |
| **GAIN** | Conversion from DN to electrons | [gain_reffile.ipynb](gain_reffile.ipynb) |
| **READNOISE** | Read-noise characterization | [readnoise_reffile.ipynb](readnoise_reffile.ipynb) |
| **AREA** | Pixel solid-angle mapping | [area_reffile.ipynb](area_reffile.ipynb) |
| **PSF / ePSF** | Empirical point-spread functions | [psf_reffile.ipynb](psf_reffile.ipynb) |
| **LINEARITY** | Detector nonlinearity correction | [linearity_reffile.ipynb](linearity_reffile.ipynb) |
