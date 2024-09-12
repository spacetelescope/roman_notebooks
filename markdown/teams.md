# RSP Team Structure and File Sharing

## Accessing Team Resources
When you log into the RSP, you will see options to log in: either using your personal account or via “team” accounts. Your team membership has been determined a priori for this validation stage. In the future, users will be able to manage their team membership through a web-based interface. The selection you make at this stage (personal or a specific team) determines who will be charged for the resources used during your session. In addition, you must select how many resources (available CPU and RAM) you want available during your session. 

After logging in and launching a session, you will have access to a persistent home storage area located at `/home/{your-username}/`. If you are a member of any teams, you can also access shared storage at `/teams/{team-name}`. All teams directories on the platform will be visible, but you only have read and write access to the teams you are a member of.

## Managing Permissions
Since files are stored in a unix-like system, you can use `chmod` to manage your team's access to files. Please see the excellent [chmod tutorial](https://catcode.com/teachmod/index.html) for a walkthrough on how this works.