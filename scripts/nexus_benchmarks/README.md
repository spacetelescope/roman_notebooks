# Computational benchmark scripts

These Python scripts provide runnable, profiled examples of Roman science
workloads covered by the [Computational Benchmarks article](https://roman-docs.stsci.edu/data-handbook/roman-research-nexus/accounts-and-credit-allocations/computational-benchmarks)
on RDox: RomanCal exposure and mosaic pipelines, Roman I-Sim simulations,
source detection and photometry, galaxy-shape measurements, Astrocut image
cutouts, Pandeia exposure-time calculations, and catalog cross-matching.

The numbered `case1()`, `case2()`, etc. functions represent distinct benchmark
scenarios or input sizes. `profile_workflows.py` supplies the shared resource
profiler, which returns a workload's result alongside CPU, memory, and
wall-clock metrics.

The article reports representative measurements, including wall-clock time,
CPU usage, memory requirements, and minimum server configurations. Use the
scripts to compare the defined workloads and estimate Roman Research Nexus
compute needs, not as fixed guarantees for other data or configurations.
Results depend on input size and source distribution, file I/O, software
versions, available memory, and parallelism. CPU hours measure total compute
consumed and are distinct from wall-clock time.