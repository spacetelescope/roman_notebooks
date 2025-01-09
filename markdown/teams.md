# Working on a Team

## Accessing Team Resources
When you log into the RRN, you will see options to log in using either your personal account or a “team” account. Your team membership has been pre-assigned for this workshop. In the future, users will be able to request and manage their team membership. The selection you make at the login stage (personal or a specific team) determines who will be charged for the resources used during the session. Additionally, you must select how many resources (CPUs and GB of RAM) you want available during your session. 

After logging in and launching a session, you will have access to a persistent home storage area located at `/home/{your-username}/`. If you are a member of any teams, you can also access shared storage at `/teams/{team-name}`. While all team directories on the nexus are visible, you will only have read and write access to the directories of teams you belong to.

## Managing Permissions

Since files are stored in a unix-like system, you can use `chmod` to manage your team's access to files. Please see the excellent [chmod tutorial](https://catcode.com/teachmod/index.html) for a walkthrough on how this works.

Each team will be assigned an admin user, who has permissions to manage all files and directories in the `teams/{team-name}/` directory. Permissions for regular users are described below.

### teams/{team-name}/

By default, within `teams/{team-name}/`, any directories or files created are group-owned by the team but user-owned by the file's creator. This means team members cannot rename or delete shared files. However, when working under your team directory, other team members **can** modify the contents of files and directories you create.

For regular users, each file or directory retains the identity of the creator as owner; aside from admins, it is always clear who created a file. 

Users who are not team members cannot access the shared folder, or any folders it contains. The team admin can manually grant access to non-team members.

Not even the team admin can delete the shared directory. 

### teams/{team-name}/{dir}/

Users can create personally-owned directories within their team directories. The default permissions are that all team members can read, write, and traverse these directories; permissions can be updated by the user who created the directory. By modifying permissions, users can create directories in the shared folder which are not writable by other group members.

It is the user's responsibility to protect files from being manipulated accidentally by other team members. 

### teams/{team-name}/{dir}/{file}

By default, files created within subdirectories of `teams/{team-name}/` will be readable by both user and group, but writeable only by user. Team members are responsible for updating the permissions of these files in order to grant additional access.

## Creating New Files and Directories

The default ownership of files and directories you create will be yourself as user/owner and either the relevant group (when under /teams) or your personal group (under $HOME) as the group. chown (change owner) and/or chgrp (change group) are used to manipulate ownership of existing files and directories. These can be found as both shell commands (i.e. can be typed into a terminal window) and programming language function calls.
