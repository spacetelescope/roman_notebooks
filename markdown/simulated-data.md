# Available Data



There are currently three types of simulated WFI images available for use with the Roman Research Nexus (RRN). These include data products from:



* [Roman I-Sim](#romanisim), which generates images that include simulated detector-level calibration features;

* The [Space Telescope Image Product Simulator](#stips) (STIPS), which simulates astronomical observing scenes;

* [The Open Universe Roman](#openuniverse) simulated preview data, converted to the Advanced Scientific Data Format (ADSF). This includes single exposures and, when available, truth catalogs for mock Roman Wide Area Survey data (Roman WAS) and the Time Domain Survey (Roman TDS).



An overview of the simulation tools and data products can be found below. At present, the majority of these files are stored in a private AWS S3 bucket accessible only within the RRN. See the [Cloud Data Access Notebook](../content/notebooks/data_discovery_and_access/data_discovery_and_access.ipynb) for more details on accessing these products.



<!--The S3 bucket (where reference files are stored on the RSP) contains two types of files: simulated Roman WFI images and the corresponding input/configuration files used to generate them. Simulated WFI images are divided into two categories: those created with Roman I-Sim, which include detector-level calibration features, and those created with the Space Telescope Image Product Simulator (STIPS), which simulate astronomical scenes. For the Roman I-Sim products, the provided configuration files include input catalogs and shell scripts used in their creation. However, for STIPS products, only the input catalog is provided.-->



## <a name="romanisim"></a>Roman I-Sim Simulated Images

[Roman I-Sim](https://github.com/spacetelescope/romanisim) generates Roman WFI imaging products by combining an input source catalog with simulated instrument and detector effects. A detailed description of the features included in the simulations can be found in the Roman I-Sim [package documentation](https://romanisim.readthedocs.io/en/latest/romanisim/overview.html).

The Roman I-Sim products have metadata and an organizational structure identical to what is expected for actual Roman data taken during operations. For example, the products are stored in ASDF files and adhere to the released version of the [WFI science data product schema](https://roman-docs.stsci.edu/data-handbook-home/wfi-data-format/data-levels-and-products) installed on the RRN. In the example [Science Workflows and Tutorials](tutorials.md), the input catalogs are provided as Enhanced Character-Separated Value (ECSV) files and combine stars from the Gaia source catalog and galaxies generated using the parametric source generation offered within the tool. It is important to note that the brightnesses of the Gaia stars is set to the Gaia r-band magnitude in all Roman filters (i.e., a flat spectral energy distribution (SED)) and that the parametric source generation process does not utilize SED information to produce sources with realistic colors.

Roman I-Sim products are created using reference files from the [Calibration Reference Data System](https://roman-docs.stsci.edu/data-handbook-home/accessing-wfi-data/crds-for-reference-files) (CRDS). Therefore, the accuracy of the instrumental effects in the simulations _is only as good as the reference files used to create them_. The current suite contains preliminary versions of reference files based on ground testing, and it is expected to improve as characterization of the ground test data continues. Questions regarding calibration reference files should be sent to the [Roman Helpdesk at STScI](https://stsci.service-now.com/roman).

The Roman I-Sim simulated products include four full-focal-plane exposures (18 detectors each) in a four-point box dither pattern near the globular cluster NGC 6535, centered at (Ra, Dec) = (270.94, -0.2) deg, using the F106 optical element. The offset in the dither pattern is approximately half-detector in both X and Y directions to ensure complete filling of the gaps between detectors. The table below shows the dither pattern used for the simulation, where the offsets are given as relative to the first point in the pattern:

| Dither Step | Offset X (arcsec) | Offset Y (arcsec) |
| --- | --- | --- |
| 0 | 0.00 | 0.00 |
| 1 | -205.20 | 0.88 |
| 2 | -204.32 | 206.08 |
| 3 | 0.88 | 205.20 |

From these four full-focal-plane exposures, we also generate a mosaic for detector 11 (WFI11) using each of the dither positions that cover the full extent of NGC 6535.

## <a name="stips"></a>STIPS Astronomical Scenes

[STIPS](https://stips.readthedocs.io/en/latest/) is an image simulator designed to quickly generate post-pipeline astronomical scenes for any number of detectors, encompassing the entire WFI FOV.  STIPS is equipped to incorporate instrumental distortion (if available), along with calibration residuals originating from flatfields, dark currents, and cosmic rays. Furthermore, it includes an estimate of Poisson and readout noise in the simulations, though it doesn't cover instrument saturation or non-linearity effects.

STIPS is particularly useful when [Pandeia](https://roman-docs.stsci.edu/simulation-tools-handbook-home/roman-wfi-exposure-time-calculator/pandeia-for-roman), the Exposure Time Calculator for the WFI, does not provide a sufficiently large simulation area, i.e., more than 25 x 25 arcseconds. Therefore,  STIPS is necessary for full-detector or multiple-detector image simulations. STIPS obtains instrument and filter parameters for the WFI directly from Pandeia and approximates Point Spread Functions (PSFs) at any pixel location by interpolating over a grid of nine evenly-distributed, detector-specific PSFs generated with [STPSF](https://roman-docs.stsci.edu/simulation-tools-handbook-home/stpsf-for-roman), the PSF modeling software for the WFI. The resulting flux measurements are within ~10% of those generated by Pandeia.

While STIPS can add error residuals (representing the remaining uncertainty after pipeline calibration), it does not start with Level 1 (L1) data products to propagate instrumental features through the output images. Additionally, the output residuals are not fully validated against the actual pipeline calibrations of L1 data products. Therefore, STIPS is not the ideal choice if high instrumental accuracy is needed. 

Simulated STIPS images are currently saved in a multi-extension FITS format, with each detector saved as a separate extension. Unlike the Roman I-Sim files described above, these files do not contain extensive WFI metadata. Input catalogs are saved as Comma-Separated Value (CSV) files.

The STIPS simulated products include:

- A full-focal-plane simulation (18 detectors) of the globular cluster M13 using F087 (z), F106 (Y), F129 (J), F158 (H), and F184 (H/K) filters

## <a name="openuniverse"></a>Open Universe Roman simulation

The Open Universe 2024 project aims to simulate overlapping images from surveys mimicking those that will be carried out by the Nancy Grace Roman Space Telescope, and the Vera C. Rubin Observatory. These data are publicly available at: https://irsa.ipac.caltech.edu/data/theory/openuniverse2024/overview.html as a set of FITS images and Parquet catalogs. As a demonstration of the capabilities of ASDF and the Nexus, Roman-specific images from this project are available on the RRN. There are two main datasets currently converted:

- Roman High Latitude Wide Area Survey single exposures in 6 photometric bands (F184, F158, F129, F213, F146, F106).

- Roman High Latitude Time Domain Survey in 7 photometric bands (F184, F158, F129, F213, F062, F106, and F087).

The images in the RRN consist of Roman images overlapping with the LSST ELAIS-S1 Deep Drilling Field (DDF), simulating the High Latitude Time Domain Survey, the High Latitude Wide Area Survey, as well as a calibration deep field for the High Latitude Wide Area Survey.

All data have been converted to ASDF format, which include, when available, the truth catalog with simulated sources overlapping the exposures. For simplicity, the ASDF files containing the simulated data follow a custom schema. 

The data is contained in the `roman` block, which contains the following sub-blocks


| Data block name | Description |
| ----------------- |--------------|
| data | 4096 × 4096 pixel images containing the accumulated total counts after the exposure|
| dq | 4096 × 4096 pixel images with the data quality flags|
| meta | Metadata block|
| catalogs | Block containing the truth catalogs of the sources whose positions lie in the image of interest |

## Spectroscopy Data

Simulated grism images from Wang et al. (2022, ApJ, 928, 1), developed as part of the Roman High Latitude Spectroscopic Survey (HLSS) Grism Simulation Products, are also available. For detailed information, please refer to the [documentation on IRSA](https://irsa.ipac.caltech.edu/data/theory/Roman/Wang2022a/).

Briefly, these simulations cover a total area of 4 square degrees and a redshift range of 0 < z < 3. The simulation products were designed to closely replicate future observations, incorporating the planned HLSS survey parameters such as detection limits, exposure times, roll angles, and dithering strategies.

For the spectroscopic extraction tutorial, we provide one grism file and one direct imaging file generated from these simulations.
