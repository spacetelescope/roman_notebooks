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
- 
These commands can be run directly in the terminal or invoked from within scripts.


