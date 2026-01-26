# Working on a Team

## Accessing Team Resources
When you log into the RRN, you can choose to start a session under your personal account or a team account. This determines who is billed for the compute resources (CPUs, RAM, storage) used during the session.
After launching a session, you have access to persistent home storage at:

`/home/{your-username}/`

If you belong to any teams, you can also access shared storage at:

`/teams/{team-name}/`

All team directories are visible on the Nexus, but you will only have read/write access to the teams you belong to.

## Managing Permissions
RRN storage uses a Unix-like permission model. You may adjust file access using standard tools such as `chmod`. (For a walkthrough, see the [chmod tutorial](https://catcode.com/teachmod/index.html).)

Each team has an assigned admin user, who has permission to manage all files and directories inside:

`/teams/{team-name}/` 

The sections below describe how permissions behave for regular team members in different parts of the directory structure.

### teams/{team-name}/
- Files or directories you create at this top level are **group-owned by the team but individually owned by you**.
- Other team members **cannot rename or delete** your files in this directory, but **can** modify their contents.
- Each file or directory retains the creator as the owner, except for team admins, who have broader permissions.
- Users who are not team members **cannot** access the directory. Admins may grant access to non-member users when needed.

**Note**: Even the team admin cannot delete the team directory itself.

### teams/{team-name}/{dir}/
Team members can create personal subdirectories in the team folder.

By default:

- All team members have **read, write, and execute (traverse)** permissions for these directories.
- The creator may restrict or modify permissions if needed—for example, to prevent others from editing certain files.

**Users are responsible for managing their own permissions** and protecting files from accidental modification.

### teams/{team-name}/{dir}/{file}
Files created inside team subdirectories:

- Are readable by both the user and the team group
- Are **writable only by the user**, unless permissions are explicitly changed
  
Team members must adjust file permissions if they want to grant additional access.

## Creating New Files and Directories
By default, any file or directory you create will be owned by you as the user, with group ownership assigned to either:
-	the relevant team group (if created under `/teams`)
-	your personal group (if created under your home directory)
  
You may change ownership using:
- `chown` — change file owner
- `chgrp` — change group ownership

These commands can be run directly in the terminal or invoked from within scripts.

## Using a Real-Time Collaboration (RTC) Server
Teams may launch a Real-Time Collaboration (RTC) server, which provides a shared JupyterLab session that multiple team members can join at the same time. Everyone connected sees the same notebook, terminals, files, and outputs in real time.

### Launching an RTC Server
To start an RTC server:
1. Go to the **spawner page**.
2. Under your team entry (e.g., `team-imviz`), click on the **Real Time Collaboration Server** link.
3. On the RTC server spawner page, choose the **image** (e.g., `roman-17.1.1`) and the **server size** (e.g., *Small Server: 2 vCPU, 16 GB RAM*) for your RTC session.
4. Click **Start server**.
   
Any team member with access to the team account may join the running RTC session.

### Important Notes About RTC Sessions
- RTC sessions provide a **shared workspace**—all users see and edit the same files and notebooks in real time.
- **RTC is not version controlled**. Changes made by any user are immediately reflected for all users, and there is no built-in version history. Teams should save copies or use external version control if they need to preserve work.
- Compute charges for RTC sessions are billed to the **team account**.

### When Should I Use an RTC Server?
RTC servers are useful when team members need to work together in the exact same environment. They support:
- **Live collaboration** on data analysis
- **Joint debugging** sessions
- **Training or walkthroughs** where one member demonstrates procedures to others
- **Short-term collaborative editing** requiring synchronized actions
  
RTC works best for **interactive, real-time collaboration**.
For independent work, version-controlled development, or long-running analysis, team members should start **individual team servers** instead.

### Stopping an RTC Server
RTC servers do not currently provide a direct “stop” option. At present, the recommended way to stop an RTC server is for all users to log out of the session. Once no users are connected and active, the RTC server will automatically shut down after 30 minutes of idle time.

To avoid unnecessary credit usage, teams should ensure that all participants log out when collaborative work is complete.

Support for manually stopping RTC servers directly from the **Admin panel** is planned and will be added in a future update.

---
*Last Updated: December 2025*
 




