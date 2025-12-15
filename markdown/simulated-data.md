# Available Data

There are currently several types of WFI imaging and spectroscopic products available for use with the Roman Research Nexus (RRN). These include:
- **Roman I-Sim simulated exposures**, which include simulated detector-level calibration features;
- **The Open Universe Roman simulated preview data**, converted to the Advanced Scientific Data Format (ASDF), including single exposures and, when available, truth catalogs for mock Roman Wide Area Survey (WAS) and Time Domain Survey (TDS) data;
- **Bright Star Ground Test Images** from the WFI thermal vacuum (TVAC) campaign;
- **Simulated grism images** developed for the spectroscopic component of the Roman High Latitude Wide Area Survey (HLWAS).

An overview of these data products can be found below. All files are stored in the **Open Data Bucket**. See the [Cloud Data Access Notebook](../notebooks/data_discovery_and_access/data_discovery_and_access.ipynb) for details on accessing these products.

## <a name="romanisim"></a>Roman I-Sim Simulated Images

[Roman I-Sim](https://github.com/spacetelescope/romanisim) generates Roman WFI imaging products by combining an input source catalog with simulated instrument and detector effects.

The Roman I-Sim products have metadata and an organizational structure identical to what is expected for actual Roman data taken during operations. The products are stored in ASDF files and adhere to the released version of the [WFI science data product schema](https://roman-docs.stsci.edu/data-handbook-home/wfi-data-format/data-levels-and-products) installed on the RRN. In the example [Science Workflows](workflows.md) and [Tutorials](tutorials.md), the input catalogs are provided as Enhanced Character-Separated Value (ECSV) files and combine stars from the Gaia source catalog with galaxies generated using the parametric source generation offered within the tool. The brightnesses of the Gaia stars are set to the Gaia r-band magnitude in all Roman filters (i.e., a flat spectral energy distribution), and the parametric source generation process does not use SED information to produce sources with realistic colors.

Roman I-Sim products are created using reference files from the [Calibration Reference Data System](https://roman-docs.stsci.edu/data-handbook-home/accessing-wfi-data/crds-for-reference-files) (CRDS). Therefore, the accuracy of the instrumental effects in the simulations is only as good as the reference files used to create them. The current suite contains preliminary versions of reference files based on ground testing, and it is expected to improve as characterization of the ground test data continues. Questions regarding calibration reference files should be sent to the [Roman Helpdesk at STScI](https://stsci.service-now.com/roman).

The Roman I-Sim simulated products include four full-focal-plane exposures (18 detectors each) in a four-point box dither pattern near the globular cluster NGC 6535, centered at (RA, Dec) = (270.94, –0.2) deg, using the F106 optical element. The offset in the dither pattern is approximately half a detector in both X and Y directions to ensure complete filling of the gaps between detectors. The table below shows the dither pattern used for the simulation, where the offsets are given relative to the first point in the pattern:


| Dither Step | Offset X (arcsec) | Offset Y (arcsec) |
| --- | --- | --- |
| 0 | 0.00 | 0.00 |
| 1 | -205.20 | 0.88 |
| 2 | -204.32 | 206.08 |
| 3 | 0.88 | 205.20 |

From these four full-focal-plane exposures, a mosaic for detector 11 (WFI11) is also generated using each of the dither positions that cover the full extent of NGC 6535.

New Roman I-Sim datasets that reproduce subsets of observations from the [Roman Community Defined Surveys](https://roman-docs.stsci.edu/roman-community-defined-surveys) will be available in the RRN by the beginning of 2026.

## <a name="openuniverse"></a>Open Universe Roman simulation

The Open Universe 2024 project aims to simulate overlapping images from surveys mimicking those that will be carried out by the Nancy Grace Roman Space Telescope and the Vera C. Rubin Observatory. These [data are publicly available](https://irsa.ipac.caltech.edu/data/theory/openuniverse2024/overview.html) as FITS images and Parquet catalogs. As a demonstration of ASDF and the Nexus, Roman-specific images from this project are available on the RRN.

Two main datasets are currently converted:
- Roman High Latitude Wide Area Survey single exposures in six photometric bands (F184, F158, F129, F213, F146, F106)
- Roman High Latitude Time Domain Survey in seven photometric bands (F184, F158, F129, F213, F062, F106, and F087)

The data in the RRN consists of Roman images overlapping the LSST ELAIS-S1 Deep Drilling Field (DDF), simulating the [High Latitude Time Domain Survey](https://roman-docs.stsci.edu/roman-community-defined-surveys/high-latitude-time-domain-survey), the [High Latitude Wide Area Survey](https://roman-docs.stsci.edu/roman-community-defined-surveys/high-latitude-wide-area-survey), as well as a calibration deep field for the High Latitude Wide Area Survey.

All data have been converted to ASDF format, which include, when available, the truth catalog with simulated sources overlapping the exposures. For simplicity, the ASDF files containing the simulated data follow a custom schema. 

The data is contained in the `roman` block, which includes the following sub-blocks:

| Data block name | Description |
| ----------------- |--------------|
| DATA | 4096 × 4096 pixel images containing the accumulated total counts after the exposure|
| DQ | 4096 × 4096 pixel images with the data quality flags|
| META | Metadata block|
| CATALOGS | Block containing the truth catalogs of the sources whose positions lie in the image of interest |

## Bright Star Ground Test Images
The Bright Star Saturation test was conducted as part of the Wide Field Instrument (WFI) thermal vacuum (TVAC) campaign to evaluate how the flight detectors behave when exposed to saturating light conditions. Nine in-focus point sources, with magnitudes spanning approximately 4 to 18 mag, were projected using a telescope simulator through the F146 filter onto grid positions across detectors 4 (WFI04) and 11 (WFI11).

The test sequence begins with an initial 4-frame exposure to verify that the commanded flux and position match expectations. This is followed by a series of interleaved exposures: single point-source exposures with 55 read frames alternating with single exposures taken without illumination (but with the F146 filter remaining in place). The sequence concludes with 18 dark exposures of 55 frames each, taken with the dark element in place.

These products have been converted to Level 1 (L1) format and are available in the Open Data Bucket to provide an example of ground test data suitable for detector characterization prior to actual flight observations. The WFI TVAC Test Data Notebook demonstrates how to extract a subset of the data, process it using romancal, and analyze saturation effects and per-frame slope variations in the vicinity of bright sources. Note that these test data will differ from in-flight observations because the telescope simulator and experimental setup do not reproduce the true observatory optics.

Additional reference material is available on the [Roman WFI TVAC2 Bright Star Saturation Test Data Mini-Release page](https://asd.gsfc.nasa.gov/roman/WFI_Bright_Star/) and in Dana Louie et al. (in prep.).

## Spectroscopy Data

Simulated grism images from Wang et al. (2022, ApJ, 928, 1), developed as part of the Roman High Latitude Spectroscopic Survey (HLSS) Grism Simulation Products, are also available. For detailed information, please refer to the [documentation on IRSA](https://irsa.ipac.caltech.edu/data/theory/Roman/Wang2022a/). These simulations cover a total area of 4 square degrees and a redshift range of 0 < z < 3. The simulation products were designed to closely replicate future observations, incorporating survey parameters such as detection limits, exposure times, roll angles, and dithering strategies.

For the [spectroscopic extraction tutorial](../notebooks/grism_spectral_extraction/grism_spectral_extraction.ipynb), one grism file and one direct imaging file generated from these simulations are provided.

---
*Last Updated: December 2025*
