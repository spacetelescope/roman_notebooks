# Working on a Team

## Accessing Team Resources
When you log into the RRN, you’ll have the option to use either your personal account or a team account. The choice you make at this stage determines who will be billed for the resources used during your session. You’ll also need to specify the amount of computing resources, CPUs and RAM, you want to allocate for your session.

After logging in and launching a session, you will have access to a persistent home storage area located at `/home/{your-username}/`. If you are a member of any teams, you can also access shared storage at `/teams/{team-name}`. While all team directories on the nexus are visible, you will only have read and write access to the directories of teams you belong to.

## Managing Permissions

Since files are stored in a unix-like system, you can use the `chmod` command to manage your team's access to files. Please see the excellent [chmod tutorial](https://catcode.com/teachmod/index.html) for a walkthrough on how this works.

Each team is assigned an admin user, who has permission to manage all files and directories within the `teams/{team-name}/` directory. Permissions for regular users are described below.

### teams/{team-name}/

By default, within teams/{team-name}/, any files or directories you create are group-owned by the team but individually owned by the creator. As a result, other team members cannot rename or delete these shared files. However, when working within the team directory, other team members **can** modify the contents of files and directories you create.

For regular users, each file or directory retains the creator as the owner, making it easy to identify who created what, except for admin users who have broader permissions.

Users who are not team members cannot access the shared directory or any of its contents. The team admin may manually grant access to non-team members if needed.

Note: Not even the team admin can delete the shared team directory itself.

### teams/{team-name}/{dir}/

Users can create personally owned directories within their team directories. By default, all team members have read, write, and execute (traverse) permissions for these directories. However, the user who created the directory can modify these permissions as needed. For example, they can restrict write access to prevent other team members from modifying the contents.

**It is the user's responsibility to manage permissions appropriately** and protect their files from accidental modification by others.

### teams/{team-name}/{dir}/{file}

By default, files created within subdirectories of teams/{team-name}/ are readable by both the user and the group, but writable only by the user. Team members are responsible for modifying file permissions if they wish to grant additional access.

## Creating New Files and Directories


By default, any files or directories you create will be owned by you as the user, with group ownership assigned to either the relevant team group (when created under /teams) or your personal group (when created under $HOME).
To change ownership of existing files or directories, you can use the chown (change owner) and chgrp (change group) commands. These tools are available both as shell commands (i.e., they can be typed into a terminal) and as function calls in programming languages.
