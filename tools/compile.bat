python tools/version_file.py
pyinstaller -w -F --exclude-module numpy --version-file "build/versionfile.txt" --add-data "./assets/icon32.ico;./assets" --add-data "./LICENSE;./" -i "assets/icon256.ico" -n RestoreWindowPos "src/main.py"
makensis "tools/installer.nsi"
python tools\choco_package.py
