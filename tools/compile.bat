python tools/version_file.py
pyinstaller -F -w --version-file "build/versionfile.txt" --add-data "./assets/icon32.ico;./assets" --add-data "./LICENSE;./" -i "assets/icon256.ico" -n RestoreWindowPos "src/main.py"
makensis "tools/installer.nsi"