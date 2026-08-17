# Tips and Tricks on the Nexus

These tips can help you use Roman Research Nexus resources efficiently and estimate the credits needed for your science workflow. Current credit rates and policies are maintained in the [Nexus documentation in RDox](https://roman-docs.stsci.edu/data-handbook-home/roman-research-nexus).

## Use `/tmp` for High-I/O Temporary Files

**Situation:** Your workflow reads or writes thousands of temporary files.

**Recommendation:** Run high-I/O intermediate steps in `/tmp`, which uses storage attached to your server, rather than in the EFS-backed [personal and team directories](./teams.md). Treat `/tmp` as temporary, server-local storage. Before stopping the server, copy any results you need to keep to `/home/{your-username}/` or `/teams/{team-name}/`.

**Takeaway:** Stage temporary files in `/tmp`, perform the high-I/O work there, and move only the final products to persistent storage.

## Choose the Smallest Server That Meets Your Needs

**Situation:** You need to select a server size for an analysis.

**Recommendation:** Consider both memory and CPU requirements. A larger server is useful when a task needs more memory, but it may not run a single-threaded task faster. Start with the smallest configuration that can complete the work reliably, then change the server type if a benchmark shows that more resources help. See [Managing Your Server](./server.md) for configuration instructions.

**Takeaway:** More CPU cores and memory consume credits at a higher rate, so use a larger server only when the workflow can benefit from it.

## Stop Servers When Work Is Complete

**Situation:** You have finished an interactive session or a long-running job.

**Recommendation:** Save your work, then stop the server from **File → Hub Control Panel → Stop My Server**. Closing a notebook or browser tab does not stop the server.

**Takeaway:** A stopped server releases compute resources and no longer accumulates compute usage.

## Benchmark Before Scaling Up

**Situation:** You need to estimate the credit cost of processing a full data set.

**Recommendation:** Run a representative pilot that includes the major operations in your workflow, such as calibration, mosaicking, simulation, photometry, shape measurement, or catalog processing. Record the number of exposures, detectors, simulations, or repetitions in the pilot, then scale the measured usage to the full program.

Include a reasonable margin for development, failed runs, and scientific iteration. Use [benchmark examples in RDox](https://roman-docs.stsci.edu/data-handbook/roman-research-nexus/benchmarking-examples-and-estimated-costs-on-the-roman-research-nexus) as an order-of-magnitude check rather than as a substitute for testing your own workflow.

**Takeaway:** A small end-to-end pilot usually produces a more realistic estimate than adding together theoretical costs for individual steps.

## Monitor Credits by Resource Type

**Situation:** You want to identify which part of a workflow is using the most credits.

**Recommendation:** Use the Credit Monitor Dashboard to review daily aggregated credit usage. Select a date range and compare total, CPU, memory, storage, or egress usage for the period when the workflow ran. You can export the filtered results to a CSV file in your home directory for later scaling or proposal planning. Team admins can also review total team usage and usage by individual team members. See [Monitoring Credit Usage](./credit_monitor.md) for instructions.

For a clean comparison, change one factor at a time, such as server size, worker count, or input volume.

**Takeaway:** Measure each resource separately so that you optimize the actual cost driver rather than assuming compute is responsible for all usage.

## Parallelize for Turnaround Time, Not Automatically for Savings

**Situation:** A workflow can use multiple threads, Dask, Ray, or several independent workers.

**Recommendation:** Compare total compute usage as well as elapsed time. Parallel execution can finish work sooner, but using more resources at once does not necessarily reduce the total credits consumed.

Use parallel processing when the application supports it and faster turnaround is valuable. For single-threaded tasks, additional cores may remain idle; choose server size primarily for the memory the task requires.

**Takeaway:** Estimate credits from total resource usage, not wall-clock runtime alone.

## Keep Only the Storage Products You Need

**Situation:** Intermediate files are accumulating in your personal or team directory.

**Recommendation:** Periodically review stored products and remove reproducible intermediates that are no longer needed. Keep the code, configuration, provenance, and final science products required to recreate or validate the analysis.

Coordinate cleanup in shared team directories before deleting files that collaborators may still use.

**Takeaway:** Storage usage depends on both data volume and retention time, so routine cleanup prevents unnecessary long-term credit consumption.

## Avoid Unnecessary Data Egress

**Situation:** You plan to download a large data set or many derived products from the Nexus.

**Recommendation:** Filter, subset, or aggregate data on the Nexus before transferring it. Download only the products required for a local workflow, archive, or collaborator.

**Takeaway:** Bringing tools to the data can reduce both transfer time and egress credit usage.

## Charge Work to the Correct Account

**Situation:** You belong to a team and are starting work for a shared science program.

**Recommendation:** Launch the session under the appropriate team account so its compute and storage usage is charged to the team's shared allocation. Team admins can use the Credit Monitor Dashboard to review aggregate usage and usage by team member.

Use an individual account for tutorials, exploration, and small tests that are not part of the team program.

**Takeaway:** Confirm the selected account before launching a substantial job; usage is tracked according to the account under which the session runs.

---
*Last updated: August 2026*
