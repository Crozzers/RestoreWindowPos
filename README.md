# RestoreWindowPos

Whenever I connect/disconnect a monitor, all of my windows jump around, resize and teleport to places they are not meant to be in.
They should just go back to their previous positions on that monitor.

The aim of this project is to fix this behaviour by detecting when a display is connected/disconnected and restoring
windows to their last known positions on that display.

The project is currently in "messy early prototype phase" but hopefully I can flesh it out further in the future.

## Installation

You will need to install NSIS in order to compile the installer for the program.

The following commands will allow you to download and install the program so that it runs when you log in.

```
git clone https://github.com/Crozzers/RestoreWindowPos.git
cd RestoreWindowPos
pip install -r requirements-dev.txt
.\compile
```

The install process will bundle the python script into an EXE and install it to your `AppData\Local\Programs` folder.
It will also add itself as a startup task, which you can then disable in the "start-up" tab of Task Manager.

## Features

* Snapshots taken every 5 seconds (will change to something longer in the future)
* Can detect monitors being connected/disconnected
* Can restore most windows to their original sizes and positions
* Can restore snapped windows

## TODO

* Creating rules for matching window names
* Test on Windows 11
* Create installer to run as a service on startup