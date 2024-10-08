# RSP Science Workflows: WFI Data Analysis 

This science workflow guides users through the discovery and access of data while working in the cloud, as well as the manipulation, visualization, and analysis of simulated Roman WFI imaging data products.



## Workflow Description

- [Data Discovery and Access](../../content/notebooks/data_discovery_and_access/data_discovery_and_access.ipynb): Access data from MAST or retrieve WFI simulated images
> Stream data directly into memory from the cloud, eliminating the need to download it locally. Access data from the STScI MAST server, which hosts datasets from active missions such as Hubble, TESS, and JWST, or retrieve simulated Roman WFI data stored in AWS. 
- [Working with ASDF](../../content/notebooks/working_with_asdf/working_with_asdf.ipynb): Explore Roman WFI Data Files
> Explore WFI data products by understanding the Advanced Scientific Data Format (ASDF). Roman WFI data products, including those generated by Roman-I-Sim, are saved in ASDF format. Learn how to manage ASDF files, read metadata, and access data arrays. To learn more about Roman WFI data levels and products, visit the [RDox pages on the WFI data format](https://roman-docs.stsci.edu/data-handbook-home/wfi-data-format).
- [Data Visualization](../../content/notebooks/data_visualization/data_visualization.ipynb): Visualize Roman WFI L2 Data Products
> Visualize your L2 data products using Matplotlib and Imviz, a tool for visualizing and quickly analyzing 2D astronomical images. Imviz is based on the Jupyter platform and includes built-in Astropy functionality. For additional background, consult the Imviz documentation on ReadTheDocs.
- Analyze Roman WFI images
    - > [Aperture photometry](../../content/notebooks/aperture_photometry/aperture_photometry.ipynb): Perform forced aperture photometry on a WFI image simulated with Roman I-sim. Learn how to measure the integrated fluxes for a set of specified source positions and aperture sizes.
    - > [Galaxy Shapes](../../content/notebooks/measuring_galaxy_shapes/measuring_galaxy_shapes.ipynb): Perform shape measurements of astronomical sources on a WFI image simulated with Roman-I-Sim. Use Galsim to perform ellipticity measurements, and learn how to fit a Sérsic model to a galaxy cutout.

![wfi-analysis-flow](../../images/wfi-data-analysis.png)


## Caveat and limitations
- The current content focuses on WFI imaging mode. Jupyter notebook tutorials and Science Workflows for spectroscopic products will be available by winter 2024.
- Content on Level 3 products, including mosaicked images, will be available by Winter 2024.
