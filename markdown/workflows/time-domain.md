# RRN Science Workflows: Time Domain

This science workflow guides users through simulating and analyzing cosmic objects that vary over time. While the current workflow focuses primarily on supernovae, the methods described can be applied to other transients and variable sources.

## Workflow Description

* [**Time Domain Simulations**](../../notebooks/time_domain_simulations/time_domain_simulations.ipynb): 

Simulate a time series of Roman WFI images of a variable/transient source (for example, a Type Ia supernova) with the Roman Instrument Simulator (I-Sim). Generate a model light curve (via sncosmo), place the transient and its host galaxy into the simulated images, produce calibrated Level-2 products, and visualize the evolving brightness across epochs.


* [**Time Domain Analysis**](../../notebooks/time_domain_analysis/time_domain_analysis.ipynb): 

Measure a transient (Type Ia supernova) in a cutout when the transient's position is known. The workflow produces background-subtracted aperture photometry and PSF-fit photometry, compares the methods, estimates the S/N, generates light-curve diagnostics, and estimates uncertainties.

<img src="https://raw.githubusercontent.com/spacetelescope/roman_notebooks/refs/heads/main/images/time-domain-workflow.jpg" alt="Time Domain Workflow" width="600" />

## Caveats and limitations

* This notebook uses forced photometry because the injected transient position is known.
* Aperture corrections are computed from STPSF encircled-energy curves.
* The demo cutouts are intentionally lightweight and are provided for demonstration only.

---
*Last Updated: August 2026*
