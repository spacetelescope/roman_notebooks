# Working on a Team

## Accessing Team Resources
When you log into the RRN, you will see options to log in using either your personal account or a “team” account. Your team membership has been pre-assigned for this workshop. In the future, users will be able to request and manage their team membership. The selection you make at the login stage (personal or a specific team) determines who will be charged for the resources used during the session. Additionally, you must select how many resources (CPUs and GB of RAM) you want available during your session. 

After logging in and launching a session, you will have access to a persistent home storage area located at `/home/{your-username}/`. If you are a member of any teams, you can also access shared storage at `/teams/{team-name}`. While all team directories on the nexus are visible, you will only have read and write access to the directories of teams you belong to.

## Managing Permissions
Since files are stored in a unix-like system, you can use `chmod` to manage your team's access to files. Please see the excellent [chmod tutorial](https://catcode.com/teachmod/index.html) for a walkthrough on how this works.
