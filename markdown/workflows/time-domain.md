# RRN Science Workflows: Time Domain 

This science workflow guides users through the simulation and analysis of cosmic objects that change over time. While the current workflow focuses primarily on a supernova, the methods described can be extanded to any variable/transient source.


## Workflow Description

* [**Time Domain Simulations**](../../notebooks/time_domain_simulations/time_domain_simulations.ipynb): 

Simulate a time series of Roman WFI images of a variable/transient source (example: Type Ia supernova) with Roman I-Sim. Generate a model light curve (via sncosmo), place the transient and its host galaxy on the detector, produce calibrated Level-2 products (or inject the variable source into L2 images), and visualize the evolving brightness across epochs.


* [**Time Domain Analysis**](../../notebooks/time_domain_analysis/time_domain_analysis.ipynb): 

Measure a transient (Type Ia supernova) in a cutout of a transient with known position. The workflow produces background-subtracted aperture photometry and PSF-fit photometry, compares methods, estimates S/N, and generates light-curve diagnostics and simple fits to the injected model.

## Caveats and limitations

* This notebook uses forced photometry because the injected transient position is known.
* Aperture corrections are computed from STPSF encircled-energy curves.
* The demo cutouts are intentionally lightweight and intended for functional tests and demonstration only.

<img src="https://raw.githubusercontent.com/spacetelescope/roman_notebooks/refs/heads/main/images/time-domain-workflow.jpg" alt="Time Domain Workflow" width="600" />

---
*Last Updated: August 2026*
