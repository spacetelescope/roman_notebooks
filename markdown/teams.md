# RSP Team Structure and File Sharing

## Accessing Team Resources
When you log into the RSP, you will see options to log in using your personal account or via “team” accounts. Your team membership has been determined a priori for this validation stage. In the future, users will be able to manage their team membership through a web-based interface. The selection you make at this stage (personal or a specific team) determines who will be charged for the resources used during your Jupyterlab session. In addition, you must select a resource type (delineated via available CPU and RAM) for your session. 

After logging in and launching a session, you will have access to a persistent home storage area, as well as persistent storage allocated to the teams of which you are a member. Your home storage area is located at `/home/jovyan/`, and the storage areas of your team memberships are mounted under `/teams/<team-name>`. All directories associated with registered teams on the platform will be visible, but you will only have read and write access to the teams you are a member of.

## Managing Permissions
Since files are stored in a unix-like system, you can use `chmod` to manage your team's access to files. Please see the excellent [chmod tutorial](https://catcode.com/teachmod/index.html) for a walkthrough on how this works.