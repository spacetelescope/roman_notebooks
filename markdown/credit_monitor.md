# Monitoring Credit Usage
The Nexus provides a built-in **Credits Dashboard** for tracking credit consumption.
For more information about Nexus credits and resource usage, see the following RDox documentation:

- [Accounts and Credit Allocations](https://roman-docs.stsci.edu/data-handbook/roman-research-nexus/accounts-and-credit-allocations) — account policies, credit allocations, and resource accounting.
- [Compute Resources](https://roman-docs.stsci.edu/data-handbook/roman-research-nexus/compute-resources) — available compute resources and associated costs.
- [Storage Resources](https://roman-docs.stsci.edu/data-handbook/roman-research-nexus/storage-resources) — persistent storage and associated costs.
- [Computational Benchmarks](https://roman-docs.stsci.edu/data-handbook/roman-research-nexus/accounts-and-credit-allocations/computational-benchmarks) — measured resource usage for representative scientific workflows.
- [Estimating Resource Usage and Costs](https://roman-docs.stsci.edu/data-handbook/roman-research-nexus/accounts-and-credit-allocations/estimating-resource-usage-and-costs) — guidance for estimating resource requirements and credit consumption.

You can launch the dashboard from the **JupyterLab Launcher**.

*Open the Launcher from the JupyterLab menu using **File → New Launcher**.*

<img src="https://raw.githubusercontent.com/spacetelescope/roman\_notebooks/refs/heads/main/images/Launcher.png" alt="JupyterLab Launcher showing the Credits Dashboard under Jupyter App" width="400" />

The dashboard allows you to:
- View daily aggregated credit usage
- Filter results by user, account, date range, and credit metric
- Review cumulative total, server, egress, EFS storage, and S3 storage credits
- Export filtered data to a CSV file in your home directory

**Team members** can also view total team usage and usage broken down by individual team members.
## Using the Dashboard
1. **Open the dashboard.** In the Launcher, select **Credits Dashboard** under **Jupyter App**.
2. **Select a user and account.** Choose the account whose usage you want to review, such as your personal account or an available team account. Team members can view usage for individual members of their teams.
3. **Set a date range** for the period you want to examine.
4. **Choose a credit metric**:
    - **Total Credits** combines all usage.
    - **Server Credits (CPU+Mem)** covers CPU and memory usage.
    - **Egress Credits** covers data transfer.
    - **EFS Storage Credits** covers persistent storage.
    - **S3 Storage Credits** covers S3 object storage.
5. **Review the daily usage plot and cumulative credit summary**, which update automatically based on your filters.
6. **Export results** using the Export CSV button.
---
*Last Updated: November 2026*
