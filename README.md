# RestoreWindowPos

Whenever I connect/disconnect a monitor, all of my windows jump around, resize and teleport to places they are not meant to be in.

This project aims to fix this behaviour by taking regular snapshots of window positions. Once it detects a display being connected/disconnected, it will restore windows to their last known positions on that display.

## Installation

Head over to the [releases page](https://github.com/Crozzers/RestoreWindowPos/releases) to grab the latest installer
for the program.

#### Updating

To update to the latest version, download the latest installer from the [releases page](https://github.com/Crozzers/RestoreWindowPos/releases) and run it. Make sure to shutdown any running instances of RestoreWindowPos beforehand, otherwise the installer won't be able to overwrite your previous install.

To shutdown RestoreWindowPos, simply right click the system tray icon and click "Quit". Wait a couple of seconds for the program to shut itself down properly then launch the latest installer.

#### Compilation

You will need to install NSIS and add it to your PATH in order to compile the installer for the program, but you can bundle the app
itself with the following commands alone:

```
git clone https://github.com/Crozzers/RestoreWindowPos.git
cd RestoreWindowPos
pip install -r requirements-dev.txt
.\tools\compile
```

The install process will bundle the python script into an EXE and install it to your `AppData\Local\Programs` folder.
It will also add itself as a startup task, which you can manage in the "start-up" tab of Task Manager.

## Features

* Snapshots taken every minute (with options for various different intervals)
* Remembers window sizes and positions and restores them when monitors are connected/disconnected
* Can restore snapped windows
* Can restore past snapshots (remembers up to 10 unique layouts)
* Easy to use installer that registers the program as a startup task
* Can pause and resume taking snapshots

## TODO

* Creating rules for matching window names
* Test on Windows 11
* Ability to "Save as" with a particular layout.
    * Ideally you would be able to save the current layout and give it a memorable name
    * Perhaps the user could then add window name rules to that layout
* Remove all not-alive windows from snapshot history
