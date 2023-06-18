# RestoreWindowPos

Whenever I connect/disconnect a monitor, all of my windows jump around, resize and teleport to places they are not meant to be in.

This project aims to fix this behaviour by taking regular snapshots of window positions. Once it detects a display being connected/disconnected, it will restore windows to their last known positions on that display.

You can also define rules for windows with specific titles and/or created by specific programs. Rules will be automatically applied to matching windows that are not part of your current snapshot (eg: windows that have been created since a snapshot was last taken).
You can also give these rules memorable names, and apply any and/or all of them at any time

## Installation

### Chocolatey

As of v0.10.0, we now have a [Chocolatey package](https://community.chocolatey.org/packages/restorewindowpos/) available. You can install it with:
```
choco install restorewindowpos
```
If you want to immediately start the program after install:
```
choco install restorewindowpos --params '"/StartAfterInstall"'
```
Chocolatey packages are generated upon a new release using [GitHub actions](https://github.com/Crozzers/RestoreWindowPos/actions). The packages are then submitted to Chocolatey for review and to be published. This process does take time, so the Chocolatey version of the package may lag behind the latest GitHub release.

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
This should handle exiting any currently running instances and installing the new version.

### Manual

To update to the latest version, download the latest installer from the [releases page](https://github.com/Crozzers/RestoreWindowPos/releases) and run it. Make sure to shutdown any running instances of RestoreWindowPos beforehand, otherwise the installer won't be able to overwrite your previous install.

To shutdown RestoreWindowPos, simply right click the system tray icon and click "Quit". Wait a couple of seconds for the program to shut itself down properly then launch the latest installer.

If the newly installed update throws an error on launch, try deleting your snapshot history file.
Hit <kbd>Win</kbd> + <kbd>R</kbd> and enter `%appdata%\..\Local\Programs\RestoreWindowPos`. Delete the `history.json` file.
If this does not resolve your issue, please [report the issue](https://github.com/Crozzers/RestoreWindowPos/issues).

## Contributing

Check the [contribution guidelines](CONTRIBUTING.md) for instructions on how contribute to the project, and instructions on how to compile the program.

## Features

* Snapshots taken every minute (with options for various different intervals)
* Remembers window sizes and positions and restores them when monitors are connected/disconnected
* Can restore snapped windows
* Can restore past snapshots (remembers up to 10 unique layouts)
* Easy to use installer that registers the program as a startup task
* Can pause and resume taking snapshots
* Create and apply rules for specific windows
* Create and apply rules for specific display configurations

## TODO

* Test on Windows 11
* Create wiki with usage instructions
* Better auto-generated layout and rule names
* Add behaviour methods to dataclasses. EG: `Rule` should have method `Rule.apply` to apply the rule
* Allow user to specify "and" or "or" matching for displays within a layout
