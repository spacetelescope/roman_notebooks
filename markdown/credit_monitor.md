# Monitoring Credit Usage
The Nexus provides a built-in **Credits Dashboard** for tracking credit consumption. For credit and account policies, see the [Roman Research Nexus overview](https://roman-docs.stsci.edu/data-handbook/roman-research-nexus) and [benchmarking examples and estimated costs](https://roman-docs.stsci.edu/data-handbook/roman-research-nexus/benchmarking-examples-and-estimated-costs-on-the-roman-research-nexus) in RDox.

You can launch the dashboard from the **JupyterLab Launcher**.

*Open the Launcher from the JupyterLab menu using **File → New Launcher***.

<img src="https://raw.githubusercontent.com/spacetelescope/roman_notebooks/refs/heads/main/images/Launcher.png" alt="JupyterLab Launcher showing the Credits Dashboard under Jupyter App" width="400" />


The dashboard allows you to:
- View daily aggregated credit usage
- Filter results by user, account, date range, and credit metric
- Review cumulative total, server, egress, and EFS storage credits
- Export filtered data to a CSV file in your home directory

**Team admins** can also view total team usage and usage broken down by individual team members.

## Using the Dashboard
1. **Open the dashboard.** In the Launcher, select **Credits Dashboard** under **Jupyter App**.
2. **Select a user and account.** Choose the account whose usage you want to review, such as your Personal Server or an available team account. Admins can choose any team member.
3. **Set a date range** for the period you want to examine.
4. **Choose a credit metric**:
   - **Total Credits** combines all usage.
   - **Server Credits (CPU+Mem)** covers CPU and memory usage.
   - **Egress Credits** covers data transfer.
   - **EFS Storage Credits** covers persistent storage.
5. **Review the daily usage plot and cumulative credit summary**, which update automatically based on your filters.
6. **Export results** using the Export CSV button.

---
*Last Updated: August 2026*
