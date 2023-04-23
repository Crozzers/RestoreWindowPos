# Contributing

Contributions are welcome. Issues, ideas and pull requests are all appreciated.

## Dev Setup

This library is built for Python 3.10 and up, although `wxPython` wheels are currently unavailable for Python 3.11.

You will need to install NSIS and add it to your PATH in order to compile the installer for the program, but you can bundle the app
itself with the following commands alone:

```
git clone https://github.com/Crozzers/RestoreWindowPos
cd RestoreWindowPos
pip install -r requirements.dev.txt
.\tools\compile.bat
```

## Releases

When publishing a release, the dev must do the following:
* Bump version number in `src/_version.py`
* Create a git tag for the release
* `git push` and `git push --tags`
* Approve chocolatey pipeline deployment
* Update release drafted by github actions
