# Simulated Data Products on the RSP

The S3 bucket (where reference files are stored on the RSP) contains two types of files: simulated Roman WFI images and the corresponding input/configuration files used to generate them. Simulated WFI images are divided into two categories: those created with Roman I-Sim, which include detector-level calibration features, and those created with the Space Telescope Image Product Simulator (STIPS), which simulate astronomical scenes. For the Roman I-Sim products, the provided configuration files include input catalogs and shell scripts used in their creation. However, for STIPS products, only the input catalog is provided.

## Roman I-Sim Simulated Images
The Roman I-Sim products are stored in Advanced Scientific Data Format (ASDF) files and adhere to the development version of the WFI science data product schema. This means that Roman I-Sim ASDF files organize data and metadata identically to how WFI data will be organized during science operations. Input catalogs are saved as Enhanced Character-Separated Value (ECSV) files and were generated using the parametric source generation offered within the tool. It is important to note that this source generation process does not utilize spectral energy distribution (SED) information to produce sources with realistic colors.

Roman I-Sim products are created using reference files from the Calibration Reference Data System (CRDS). Therefore, the instrumental effects in the simulations are only as accurate as the reference files used to create them. Many of the reference files in CRDS are currently estimated based on mission requirements or models of the observatory/WFI and do not yet reflect recent ground testing campaigns. Additionally, some reference files (e.g., photometric calibration) are obtained for a single, idealized detector.

The Roman I-Sim simulated products include:
- A simulation of a dense region (~12.5 deg2) composed of 108 stars and 106 galaxies
    - Two full-focal-plane exposures (18 detectors each) centered at (RA, Dec) = (0.50, 0.50) deg in the F129 (J) and F158 (H) optical elements.
    - Two full-focal-plane exposures (18 detectors each) centered at (RA, Dec) = (0.47, 0.51) deg in the F129 (J) and F158 (H) optical elements.
- A simulation of a 'high-latitude' region (~0.5 deg2) composed of 3 x 104 stars and 104 galaxies.
    - One detector (WFI01) in F106 (Y) with the WFI focal plane centered at (RA, Dec) = (0.0, 0.0) deg



## STIPS Astronomical Scenes
STIPS files are currently saved in a multi-extension FITS format, with each detector saved as a separate extension. These files do not contain extensive WFI metadata. Input catalogs are saved as Comma-Separated Value (CSV) files.
The STIPS simulated products include:
- A full-focal-plane simulation (18 detectors) of the globular cluster M13 using F087 (z), F106 (Y), F129 (J), F158 (H), and F184 (H/K) filters
