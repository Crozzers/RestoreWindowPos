python tools/version_file.py
pyinstaller -F -w --version-file "build/versionfile.txt" --collect-all infi.systray --add-data "./assets/icon32.ico;./assets" -i "assets/icon256.ico" -n RestoreWindowPos "src/main.py"
makensis "src/installer.nsi"