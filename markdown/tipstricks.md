# Tips and Tricks on the Nexus

These tips can help you use Roman Research Nexus resources efficiently and estimate the credits needed for your science workflow. For information about credit allocations, available resources, and estimating costs, see [Accounts and Credit Allocations](https://roman-docs.stsci.edu/data-handbook/roman-research-nexus/accounts-and-credit-allocations), [Compute Resources](https://roman-docs.stsci.edu/data-handbook/roman-research-nexus/compute-resources), [Storage Resources](https://roman-docs.stsci.edu/data-handbook/roman-research-nexus/storage-resources), and [Estimating Resource Usage and Costs](https://roman-docs.stsci.edu/data-handbook/roman-research-nexus/accounts-and-credit-allocations/estimating-resource-usage-and-costs) in RDox.
## Reuse Existing Roman Data Products
**Situation:** Your analysis requires large volumes of Roman imaging or catalog data.

**Recommendation:** Check whether the data products you need are already available through MAST before running your own processing. Use existing calibrated exposures, mosaics, and catalogs when they meet your scientific requirements. When possible, stream data directly from [MAST](https://mast.stsci.edu/search/ui/#/roman) instead of downloading and storing complete datasets on the Nexus.

**Takeaway:** Reusing existing products and streaming data can reduce compute time, storage requirements, and credit consumption.
## Choose the Smallest Server That Meets Your Needs
**Situation:** You need to select a server size for an analysis.

**Recommendation:** Consider both memory and CPU requirements. A larger server is useful when a task needs more memory, but it may not run a single-threaded task faster. Start with the smallest configuration that can complete the work reliably, then change the server type if a benchmark shows that more resources help. See [Compute Resources](https://roman-docs.stsci.edu/data-handbook/roman-research-nexus/compute-resources) for available server configurations and [Managing Your Server](server.md) for configuration instructions.

**Takeaway:** More CPU cores and memory consume credits at a higher rate, so use a larger server only when the workflow can benefit from it.
## Benchmark Before Scaling Up
**Situation:** You need to estimate the credit cost of processing a full data set.

**Recommendation:** Run a representative pilot that includes the major operations in your workflow, such as calibration, mosaicking, simulation, photometry, shape measurement, or catalog processing. Record the number of exposures, detectors, simulations, or repetitions in the pilot, then scale the measured usage to the full program.

Include a reasonable margin for development, failed runs, and scientific iteration. See [Computational Benchmarks](https://roman-docs.stsci.edu/data-handbook/roman-research-nexus/accounts-and-credit-allocations/computational-benchmarks) for measured examples of scientific workflows, and [Estimating Resource Usage and Costs](https://roman-docs.stsci.edu/data-handbook/roman-research-nexus/accounts-and-credit-allocations/estimating-resource-usage-and-costs) for guidance on estimating credit consumption. Use these resources as order-of-magnitude checks rather than substitutes for testing your own workflow.

**Takeaway:** A small end-to-end pilot usually produces a more realistic estimate than adding together theoretical costs for individual steps.
## Parallelize for Turnaround Time, Not Automatically for Savings
**Situation:** A workflow can use multiple threads, Dask, Ray, or several independent workers.

**Recommendation:** Compare total compute usage as well as elapsed time. Parallel execution can finish work sooner, but using more resources at once does not necessarily reduce the total credits consumed.

Use parallel processing when the application supports it and faster turnaround is valuable. For single-threaded tasks, additional cores may remain idle; choose server size primarily for the memory the task requires.

**Takeaway:** Estimate credits from total resource usage, not wall-clock runtime alone.
## Use `/tmp` for High-I/O Temporary Files
**Situation:** Your workflow reads or writes thousands of temporary files or repeatedly accesses large intermediate datasets.

**Recommendation:** Run high-I/O intermediate steps in `/tmp`, which uses storage attached to your server, rather than in the EFS-backed personal and team directories. This can reduce EFS read and write operations, which consume credits in addition to persistent storage.

Treat `/tmp` as temporary, server-local storage. Before stopping the server, copy any results you need to keep to `/home/{your-username}/` or `/teams/{team-name}/`.

For more information about EFS storage and I/O costs, see [Storage Resources](https://roman-docs.stsci.edu/data-handbook/roman-research-nexus/storage-resources).

**Takeaway:** Use `/tmp` for high-I/O intermediate processing and move only the products you need to retain to persistent storage.
## Choose the Right Storage and Clean Up What You Don't Need
**Situation:** You need to store intermediate files, working datasets, or large science products on the Nexus.

**Recommendation:** Use EFS storage (`/home/{your-username}/` or `/teams/{team-name}/`) for smaller files that require frequent access, such as notebooks, scripts, configuration files, and intermediate products. Use S3 for larger datasets and science products that need to be retained over longer periods.

Periodically review your storage and delete files that are no longer needed, particularly reproducible intermediate products. Keep the code, configuration, provenance, and final science products required to recreate or validate your analysis. Coordinate cleanup in shared team storage before deleting files that collaborators may still use.

For more information, see [Storage Resources](https://roman-docs.stsci.edu/data-handbook/roman-research-nexus/storage-resources).

**Takeaway:** Choose EFS for smaller, frequently accessed files and S3 for larger, longer-lived datasets. Regularly remove unnecessary files to reduce storage consumption.
## Avoid Unnecessary Data Egress
**Situation:** You plan to download a large data set or many derived products from the Nexus.

**Recommendation:** Filter, subset, or aggregate data on the Nexus before transferring it. Download only the products required for a local workflow, archive, or collaborator.

**Takeaway:** Bringing tools to the data can reduce both transfer time and egress credit usage.
## Charge Work to the Correct Account
**Situation:** You belong to a team and are starting work for a shared science program.

**Recommendation:** Launch the session under the appropriate team account so its compute usage is charged to the team's shared allocation. Persistent storage usage is accounted for separately. All team members can use the Credits Dashboard to review aggregate team usage and usage by individual team members.

Use an individual account for tutorials, exploration, and small tests that are not part of the team program.

**Takeaway:** Confirm the selected account before launching a substantial job; compute usage is charged to the account under which the session runs
## Monitor Credits by Resource Type
**Situation:** You want to identify which part of a workflow is using the most credits.

**Recommendation:** Use the Credits Dashboard to review daily aggregated credit usage. Select a date range and compare total, server (CPU and memory), egress, EFS storage, and S3 storage credits for the period when the workflow ran. You can export the filtered results to a CSV file in your home directory for later scaling or proposal planning.
All team members can also review total team usage and usage broken down by individual team members. See [Monitoring Credit Usage](credit_monitor.md) for instructions.

For a clean comparison, change one factor at a time, such as server size, worker count, or input volume.

**Takeaway:** Measure each resource separately so that you optimize the actual cost driver rather than assuming compute is responsible for all usage.
## Stop Servers When Work Is Complete
**Situation:** You have finished an interactive session or a long-running job.

**Recommendation:** Save your work, then stop the server from **File → Hub Control Panel → Stop My Server**. Closing a notebook or browser tab does not stop the server.

**Takeaway:** A stopped server releases compute resources and no longer accumulates compute usage.

---
*Last updated: November 2026*
