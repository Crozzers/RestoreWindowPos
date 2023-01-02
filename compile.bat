pyinstaller -F -w --collect-all infi.systray --add-data "./assets/icon32.ico;./assets" -i "assets/icon256.ico" -n RestoreWindowPos "src/main.py"
makensis "src/installer.nsi"