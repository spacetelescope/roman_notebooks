# RRN Science Workflows: Roman Data Essentials

Roman Data Essentials introduces the foundational concepts and tools needed to begin working with Roman data. Designed for users new to Roman or astronomy data analysis, it combines background resources with guided notebook tutorials on discovering, accessing, understanding, and visualizing Roman data, as well as exploring planned survey footprints.

## Before You Begin

Before starting the notebook tutorials, review the [Jupyter basics](../jupyter.md) to become familiar with running and interacting with notebooks. Then explore the [Roman Mission Introduction](../roman_Intro.md) for background on Roman's science goals, instruments, and data products.

## Workflow Overview

1. [**Data Discovery and Access**](../../notebooks/data_discovery_and_access/data_discovery_and_access.ipynb)

   Search for and access simulated Roman Wide Field Instrument (WFI) data in the Nexus and observations from active missions through the Barbara A. Mikulski Archive for Space Telescopes (MAST). Learn how to identify relevant observations and retrieve data products for further exploration.

2. [**Working with ASDF**](../../notebooks/working_with_asdf/working_with_asdf.ipynb)

   Explore the Advanced Scientific Data Format used for Roman data products. Learn how to inspect metadata, access data arrays, and understand the organization of Roman WFI files.

3. **Data Visualization**

   Explore image data, inspect instrument artifacts, and apply common visualization techniques using two complementary approaches:

    - [**Create Static Images with Matplotlib**](../../notebooks/data_visualization/data_visualization.ipynb): Display Roman images and create figures that can be saved or included in reports.
    - [**Interactively Explore Images with Jdaviz**](../../notebooks/data_visualization/jdaviz_data_visualization.ipynb): Examine, navigate, and compare image data using interactive controls.

### Additional Exploration

- [**Footprint Visualization**](../../notebooks/footprint_visualization/footprint_visualization.ipynb)

  Explore planned Roman survey footprints and determine whether, when, and how Roman may observe a position on the sky. This tutorial can be completed independently of the preceding data-focused tutorials.

## Scope and Limitations

- This workflow provides an introduction to Roman data products and common analysis tools. It does not cover calibration pipelines or advanced scientific analysis.
- Data availability and platform functionality may continue to evolve during Early Access.

---
*Last Updated: August 2026*
