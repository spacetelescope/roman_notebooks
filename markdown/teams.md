# Working on a Team

## Accessing Team Resources
When you log into the RRN, you will see options to log in using either your personal account or a “team” account. Your team membership has been pre-assigned for this workshop. In the future, users will be able to request and manage their team membership. The selection you make at the login stage (personal or a specific team) determines who will be charged for the resources used during the session. Additionally, you must select how many resources (CPUs and GB of RAM) you want available during your session. 

After logging in and launching a session, you will have access to a persistent home storage area located at `/home/{your-username}/`. If you are a member of any teams, you can also access shared storage at `/teams/{team-name}`. While all team directories on the nexus are visible, you will only have read and write access to the directories of teams you belong to.

## Managing Permissions

Since files are stored in a unix-like system, you can use `chmod` to manage your team's access to files. Please see the excellent [chmod tutorial](https://catcode.com/teachmod/index.html) for a walkthrough on how this works.

Each team will be assigned an admin user, who has permissions to manage all files and directories in the `teams/{team-name}/` directory. Permissions for regular users are described below.

### teams/{team-name}/

By default, within `teams/{team-name}/`, the setgid bit is set, causing any directories or files created here or below to be group-owned by this team but user-owned by whoever creates the file.  Initially, the user sticky bit is also set on this directory so that members of the group can create their own artifacts but not rename or delete those of other members.

For regular users,  each file or directory retains the identity of the creator as owner,  so aside from admins we can discern who created what.  Not even the team admin can delete the group directory itself due to the permissions of teams.  By default,  when working under your team directory, you will assign write privileges to the team enabling them to modify files and directories you create.

Because of these permissions, users who are not team members cannot access this level or below even to read or traverse.  Note that by carefully manipulating the "other" bits, non-team members could be granted traversal and/or read access to nested directories and files, with that configuration controllable by the team admin.

### teams/{team-name}/{dir}/

Users can create personally-owned directories within their team directories. The default permissions are that all team members can read, write, and traverse these directories, and these permissions can be updated by the user who created them. This property enables admins to create directories here which are not writable by other group members.

It will be the user's responsibility to set the sticky bit to protect files from being manipulated accidentally by other team members. The group assignment is driven by the setgid bit on the /teams/<group> directory where this artifact is created.

### teams/{team-name}/{dir}/{file}

By default, files created within the `teams/{team-name}/` directory will be readable by both user and group, writeable only by user. Team members are responsible for updating the permissions of these files in order to grant additional access.

## Creating New Files and Directories

The default ownership of files and directories you create will be yourself as user/owner and either the relevant group (when under /teams) or your personal group as group (under $HOME). chown and/or chgrp are used to manipulate ownership of existing files and directories.   These can be found as both shell commands and programming language function calls.

The default permissions of new files and directories you create are largely controlled by the `umask` feature of Linux/UNIX.  These are user=rwx group=rwx other=rx when umask=002 octal. The umask value is used to select the permission bits which should NOT be set.  Permission bits can be altered after creation using the chmod shell or various Programming Language functions.
