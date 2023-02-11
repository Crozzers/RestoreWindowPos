# RestoreWindowPos

Whenever I connect/disconnect a monitor, all of my windows jump around, resize and teleport to places they are not meant to be in.

This project aims to fix this behaviour by taking regular snapshots of window positions. Once it detects a display being connected/disconnected, it will restore windows to their last known positions on that display.

You can also define rules for windows with specific titles and/or created by specific programs. Rules will be automatically applied to matching windows that are not part of your current snapshot (eg: windows that have been created since a snapshot was last taken).
You can also give these rules memorable names, and apply any and/or all of them at any time

## Installation

Head over to the [releases page](https://github.com/Crozzers/RestoreWindowPos/releases) to grab the latest installer
for the program.

#### Updating

To update to the latest version, download the latest installer from the [releases page](https://github.com/Crozzers/RestoreWindowPos/releases) and run it. Make sure to shutdown any running instances of RestoreWindowPos beforehand, otherwise the installer won't be able to overwrite your previous install.

To shutdown RestoreWindowPos, simply right click the system tray icon and click "Quit". Wait a couple of seconds for the program to shut itself down properly then launch the latest installer.

If the newly installed update throws an error on launch, try deleting your snapshot history file.
Hit <kbd>Win</kbd> + <kbd>R</kbd> and enter `%appdata%\..\Local\Programs\RestoreWindowPos`. Delete the `history.json` file.
If this does not resolve your issue, please [report the issue](https://github.com/Crozzers/RestoreWindowPos/issues).

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

Currently, the project can only be bundled using Python 3.10, as it requires Python 3.10's type hint features and `wxPython`, which only has installation wheels up to Python 3.10.

## Features

* Snapshots taken every minute (with options for various different intervals)
* Remembers window sizes and positions and restores them when monitors are connected/disconnected
* Can restore snapped windows
* Can restore past snapshots (remembers up to 10 unique layouts)
* Easy to use installer that registers the program as a startup task
* Can pause and resume taking snapshots
* Create and apply rules for specific windows

## TODO

* Test on Windows 11
* Ability to "Save as" with a particular layout.
    * Ideally you would be able to save the current layout and give it a memorable name
    * This will likely auto-create rules matching the current windows
* Central rule manager GUI
    * And also, probably as part of this central GUI, a settings panel to tweak the less useful settings, like "Save frequency"