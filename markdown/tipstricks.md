# Tips and Tricks on the Nexus

This documentation lists various tips and tricks when working on the Roman Research Nexus. These are presented in no particular order, but we do provide context for situations to which they may apply.

## Increased Costs for EFS I/O

**Situation:** You are reading and writing thousands of temporary files as part of your workflow. 

**Background:** Amazon Web Services (AWS) Elastic File System (EFS) is the system used to create the user and team directories you see in the Nexus file system. AWS EFS incurs a cost for reading and writing files, and if you plan to have very high I/O rates (for example, you are creating thousands of temporary files), you should not use EFS.

**Instead:** You can use the `/tmp` folder for high file I/O operations. The `/tmp` folder is mapped to the attached storage on your server and will not incur additional file I/O costs unlike EFS. The `/tmp` folder exists at the top level of the filesystem, so you simply need to `cd /tmp` to access it from a terminal.

**Takeaway:** If you choose to use EFS for high file I/O operations, you will see a faster reduction in your Nexus credits compared to if you used `/tmp` for temporary files.

---
*Last updated: August 2026*