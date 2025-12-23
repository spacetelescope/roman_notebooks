# Managing Your Server
Your Nexus server provides the compute environment that runs JupyterLab. You can start, stop, or reconfigure your server from the **Hub Control Panel**:

**File → Hub Control Panel**

## Starting Your Server
Your server starts automatically when you open JupyterLab if no server is running.

You can also start it manually from:
**File → Hub Control Panel → My Server**

If the server is stopped, **My Server** will start it and take you to JupyterLab.

## Stopping Your Server
Stopping ends your session and releases compute resources. Your files are not affected.

To stop your server:
**File → Hub Control Panel → Stop My Server**

Stopping is recommended when you are done working or when you need to relaunch your session with a different image or server type.

## Automatic Shutdown After Idle Time
To conserve shared compute resources, servers are automatically shut down after **1 hour of inactivity**.

A server is considered idle when there is no active user interaction (for example, no notebook execution or terminal activity). When the idle limit is reached, the server is stopped and the session ends.

Stopping a server does not affect files stored in your home directory or team directories. Any unsaved work in notebooks or terminals will be lost.

If you plan to step away for an extended period, save your work before leaving your session.

## Changing Your Server Type (Image / Size)
You can change your server configuration only during startup.

To change it:
1. **Stop My Server**
2. Go to **Start My Server**
3. The server options page appears (image, server size)
4. Select your configuration and click **Launch**

Changes take effect immediately for the new session. For additional details on platform images and server availability, see the [related article in RDox](https://roman-docs.stsci.edu/data-handbook-home/roman-research-nexus).

## Named Servers
In addition to your default server, you can create additional independent servers.

To create one:
1. Go to **File → Hub Control Panel**
2. Under **Named Servers**, enter a name
3. Click **Add New Server**
   
Each named server has its own environment and storage. You can start or stop them independently.

Use named servers when you need separate workspaces—for example, testing a clean environment without affecting your primary one.

## When to Use Each Action
- **Stop** when you're done working or want to change configurations
- **Start** to launch a new session
- **Change server type** when you need more or less compute
- **Named servers** for parallel or isolated environments

For information on Real Time Collaboration Servers, please see the [Working on a Team Page](./teams.md).

---
*Last updated: December 2025*
