# RRN Science Workflows: WFI Observations Planning
This science workflow is designed to support planning of Roman Wide Field Instrument (WFI) observations by combining exposure estimation, instrument characterization, and survey-level planning tools. Together, these components help users evaluate observing strategies, survey geometry, and observing conditions in support of Roman proposal development and early-stage analyses.

## Workflow Overview
- [**RIST (Roman Interactive Sensitivity Tool)**](../../notebooks/rist/rist.ipynb)

  Use RIST to obtain rapid estimates of signal-to-noise ratio (SNR) for on-axis point sources with simple spectral assumptions. RIST provides an efficient way to explore how SNR varies with source brightness, filter choice, and exposure time, and is often used for early-stage feasibility assessments. For more information, please refer to the [Roman Interactive Sensitivity Tool documentation in RDox](https://roman-docs.stsci.edu/simulation-tools-handbook-home/simulation-development-utilities/roman-interactive-sensitivity-tool)
  
- [**STPSF**](../../notebooks/stpsf/stpsf.ipynb)
  
  Generate simulated WFI point spread functions (PSFs) using STPSF to understand the instrument’s spatial response across the field of view and as a function of wavelength. Visit the [STPSF for Roman in RDox](https://roman-docs.stsci.edu/simulation-tools-handbook-home/stpsf-for-roman) to learn more about the software.
    
- [**Synphot**](../../notebooks/synphot/synphot.ipynb)

  Estimate observed fluxes for empirical or model spectral energy distributions as they would be measured by the WFI. To learn more, refer to the [stsynphot for Roman documentation in RDox](https://roman-docs.stsci.edu/simulation-tools-handbook-home/simulation-development-utilities/synphot-for-roman).
  
- [**Pandeia**](../../notebooks/pandeia/pandeia.ipynb)

  Use Pandeia, the Roman Exposure Time Calculator, to quantitatively define exposure parameters required to achieve science goals. Pandeia supports detailed configuration of observing modes and is typically used once approximate requirements have been identified with RIST. For more information, please refer to the [Pandeia for Roman documentation in RDox](https://roman-docs.stsci.edu/simulation-tools-handbook-home/pandeia-for-roman).

- **Survey and observing-strategy evaluation tools**

  After exposure parameters are defined with Pandeia, additional tools can be used to assess survey geometry and observing conditions:

  - [**STIPS (Space Telescope Image Product Simulator)**](../../notebooks/stips/stips.ipynb) simulates realistic astronomical scenes over a full WFI field of view or multiple detectors, enabling validation of exposure choices in crowded or extended fields.
  - [**Footprint Visualization Tool**](../../notebooks/footprint_visualization/footprint_visualization.ipynb) provides on-sky visualizations of APT program footprints and exposure coverage, supporting survey tiling and geometry evaluation.
  - [**Roman Background Visualization Tool (RBVT)**](../../notebooks/background_visualization_tool/RBVT.ipynb) enables exploration of time-variable sky background components as a function of sky position and calendar date, supporting assessment of observing conditions and scheduling constraints.

These tools are complementary and are often used iteratively to refine observing strategies. User documentation is available at the [Simulation Tools User Manual in RDox](https://roman-docs.stsci.edu/simulation-tools-handbook-home).

<img src="https://raw.githubusercontent.com/spacetelescope/roman_notebooks/refs/heads/main/images/wfi-obs-plan.jpg" alt="WFI Data Analysis Workflow" width="400" />

## Caveats and Limitations
- This workflow primarily targets WFI imaging-mode planning. While some tools support spectroscopic configurations, comprehensive spectroscopic planning workflows will be expanded in future releases.
- Users should expect to iterate between steps (e.g., between Pandeia, background evaluation, and scene simulations) as science requirements are refined.

---
*Last Updated: December 2025* 
