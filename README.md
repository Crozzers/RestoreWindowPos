# RestoreWindowPos

Whenever I connect/disconnect a monitor, all of my windows jump around, resize and teleport to places they are not meant to be in.

This project aims to fix this behaviour by taking regular snapshots of window positions. Once it detects a display being connected/disconnected, it will restore windows to their last known positions on that display.

You can also define rules for windows with specific titles and/or created by specific programs. Rules will be automatically applied to matching windows that are not part of your current snapshot (eg: windows that have been created since a snapshot was last taken).
You can also give these rules memorable names, and apply any and/or all of them at any time

## Installation

### Chocolatey

The [RestoreWindowPos Chocolatey package](https://community.chocolatey.org/packages/restorewindowpos/) can be installed with this command:
```
choco install restorewindowpos
```

Chocolatey packages are auto-generated each release using [GitHub actions](https://github.com/Crozzers/RestoreWindowPos/actions). The packages are then submitted to Chocolatey for review and to be published. This process does take time, so the Chocolatey version of the package may lag behind the latest GitHub release.

#### Package Parameters

| Parameter            | Descrption                                        |
|----------------------|---------------------------------------------------|
| `/StartAfterInstall` | Launch the program after installation is finished |
| `/DesktopShortcut`   | Create a desktop shortcut for the program         |
| `/StartMenuShortcut` | Create a start menu shortcut for the program      |

Example:
```
choco install restorewindowpos --params '"/StartAfterInstall /DesktopShortcut /StartMenuShortcut"'
```

### Manual install

Head over to the [releases page](https://github.com/Crozzers/RestoreWindowPos/releases) to grab the latest installer
for the program.

## Updating

### Chocolatey

If you used Chocolatey to install, it should be as simple as running:
```
choco upgrade restorewindowpos
```
And if you want to immediately restart the program after upgrading:
```
choco upgrade restorewindowpos --params '"/StartAfterInstall"'
```
This should handle exiting any currently running instances and installing the new version. If it doesn't work, or if the new files aren't properly copied across, try manually shutting down any running instances and upgrading after that.

### Manual

To update to the latest version, download the latest installer from the [releases page](https://github.com/Crozzers/RestoreWindowPos/releases) and run it. Make sure to shutdown any running instances of RestoreWindowPos beforehand, otherwise the installer won't be able to overwrite your previous install.

To shutdown RestoreWindowPos, simply right click the system tray icon and click "Quit". Wait a couple of seconds for the program to shut itself down properly then launch the latest installer.

If the newly installed update throws an error on launch, try moving your snapshot history file.
Hit <kbd>Win</kbd> + <kbd>R</kbd> and enter `%localappdata%\Programs\RestoreWindowPos`. Rename `history.json` to `history.json.old`.
If this does not resolve your issue, please [report the issue](https://github.com/Crozzers/RestoreWindowPos/issues).

## Contributing

Check the [contribution guidelines](CONTRIBUTING.md) for instructions on how contribute to the project, and instructions on how to compile the program.

## Features

* Regular snapshots of current window layout (with options for various different intervals)
* Remembers window sizes and positions and restores them when monitors are connected/disconnected
* Can restore snapped windows
* Can restore past snapshots
* Easy to use installer that registers the program as a startup task
* Create and apply rules for specific windows
* Create and apply rules for specific display configurations
* React to new windows spawning and take some predefined action
