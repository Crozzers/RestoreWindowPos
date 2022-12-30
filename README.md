# RestoreWindowPos

Whenever I connect/disconnect a monitor, all of my windows jump around, resize and teleport to places they are not meant to be in.
They should just go back to their previous positions on that monitor.

The aim of this project is to fix this behaviour by detecting when a display is connected/disconnected and restoring
windows to their last known positions on that display.

The project is currently in "messy early prototype phase" but hopefully I can flesh it out further in the future.

## Running the program

Run the program in an admin powershell prompt.

## Features

* Snapshots taken every 5 seconds (will change to something longer in the future)
* Can detect monitors being connected/disconnected
* Can restore most windows to their original sizes and positions
* Can restore snapped windows

## TODO

* Creating rules for matching window names
* Test on Windows 11
* Create installer to run as a service on startup