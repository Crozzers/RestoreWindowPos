; Based off of the EdgeDeflector installer
; https://github.com/da2x/EdgeDeflector/blob/master/EdgeDeflector/resources/nsis_installer.nsi
Unicode true
; UTF-8 BOM!

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"
!include "nsDialogs.nsh"

RequestExecutionLevel user
ShowInstDetails show

; Installer for RestoreWindowPos
BrandingText "RestoreWindowPos By Crozzers"

!define PRODUCT "RestoreWindowPos"
!define DESCRIPTION "Restore window positions when displays are connected and disconnected"
!getdllversion "..\dist\${PRODUCT}.exe" VERSION_
!define VERSION "${VERSION_1}.${VERSION_2}.${VERSION_3}.${VERSION_4}"

VIAddVersionKey "ProductName" "${PRODUCT} Installer"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "FileDescription" "Install ${PRODUCT} ${VERSION}"
VIAddVersionKey "LegalCopyright" "© Crozzers (github.com/Crozzers) 2024"

; use the version thing pyinstaller in the future
; https://stackoverflow.com/questions/14624245/what-does-a-version-file-look-like
VIFileVersion "${VERSION}"
VIProductVersion "${VERSION}"

Name "${PRODUCT} Installer"

OutFile "..\dist\${PRODUCT}_install.exe"

; Default installation directory
InstallDir $LOCALAPPDATA\Programs\${PRODUCT}

; Store install dir in the registry
InstallDirRegKey HKCU "SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\${PRODUCT}.exe" "Path"

; MUI Config
!define MUI_ICON "../assets/icon256.ico"

; Installer pages
!insertmacro MUI_PAGE_DIRECTORY
Page custom ShortcutPage ShortcutPageLeave
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\${PRODUCT}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch ${PRODUCT}"
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
UninstPage uninstConfirm
UninstPage instfiles


Var StartMenuShortcut
Var DesktopShortcut

Function ShortcutPage
  nsDialogs::Create 1018
  Pop $0

  # create checkboxes and set default state to checked
  ${NSD_CreateCheckbox} 10u 10u 200u 12u "Create Start-Menu Shortcut"
  Pop $1
  ${NSD_Check} $1
  ${NSD_CreateCheckbox} 10u 30u 200u 12u "Create Desktop Shortcut"
  Pop $2

  # Show the dialog
  nsDialogs::Show
FunctionEnd


Function ShortcutPageLeave
  # store checkbox states in vars
  ${NSD_GetState} $1 $StartMenuShortcut
  ${NSD_GetState} $2 $DesktopShortcut
FunctionEnd


Function checkLaunchParam
  ${GetParameters} $0
  ClearErrors
  ${GetOptions} $0 "/StartAfterInstall" $1
  ${IfNot} ${Errors}
      Exec "$INSTDIR\${PRODUCT}.exe"
  ${EndIf}
FunctionEnd


Section "Installer"
  SetAutoClose false
  AddSize 8

  ; Set output path to the installation directory.
  SetOutPath $INSTDIR

  ; Install the program
  File "..\dist\${PRODUCT}.exe"

  ; Path registration
  WriteRegStr HKCU "SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\${PRODUCT}.exe" "" "$INSTDIR\${PRODUCT}.exe"
  WriteRegStr HKCU "SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\${PRODUCT}.exe" "Path" "$INSTDIR"

  ; Program class registration
  WriteRegStr HKCU "SOFTWARE\Classes\${PRODUCT}\Application" "ApplicationName" "${PRODUCT}"
  WriteRegStr HKCU "SOFTWARE\Classes\${PRODUCT}\DefaultIcon" "" "$INSTDIR\${PRODUCT}.exe,0"
  WriteRegStr HKCU "SOFTWARE\Classes\${PRODUCT}\shell\open\command" "" '"$INSTDIR\${PRODUCT}.exe"'
  WriteRegStr HKCU "SOFTWARE\Classes\${PRODUCT}\Capabilities" "ApplicationName" "${PRODUCT}"
  WriteRegStr HKCU "SOFTWARE\Classes\${PRODUCT}\Capabilities" "ApplicationIcon" "$INSTDIR\${PRODUCT}.exe,0"
  WriteRegStr HKCU "SOFTWARE\Classes\${PRODUCT}\Capabilities" "ApplicationDescription" "${DESCRIPTION}"

  ; Application registration
  WriteRegStr HKCU "SOFTWARE\Classes\Applications\${PRODUCT}.exe\DefaultIcon" "" "$INSTDIR\${PRODUCT}.exe,0"

  ; Program registration
  WriteRegStr HKCU "SOFTWARE\RegisteredApplications" "${PRODUCT}" "SOFTWARE\Classes\${PRODUCT}\Capabilities"

  ; Run on startup
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "RestoreWindowPos" '"$InstDir\${PRODUCT}.exe"'

  ; Add start menu shortcut if option enabled
  ${IF} $StartMenuShortcut <> 0
    createShortCut "$SMPROGRAMS\${PRODUCT}.lnk" "$INSTDIR\${PRODUCT}.exe" "--open-gui" "" "" SW_SHOWNORMAL
  ${ENDIF}

  ${IF} $DesktopShortcut <> 0
    createShortCut "$DESKTOP\${PRODUCT}.lnk" "$INSTDIR\${PRODUCT}.exe" "--open-gui" "" "" SW_SHOWNORMAL
  ${ENDIF}

  ; Install the uninstaller
  WriteUninstaller "${PRODUCT}_uninstall.exe"

  ; Register the uninstaller
  WriteRegStr HKCU "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" "DisplayName" "${PRODUCT}"
  WriteRegStr HKCU "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" "DisplayIcon" "$INSTDIR\${PRODUCT}.exe,0"
  WriteRegStr HKCU "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" "DisplayVersion" "${VERSION}"

  WriteRegStr HKCU "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" "UninstallString" "$INSTDIR\${PRODUCT}_uninstall.exe"

  WriteRegDWORD HKCU "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" "NoModify" 1
  WriteRegDWORD HKCU "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" "NoRepair" 1

  ; Estimated installation size
  SectionGetSize 0 $0
  WriteRegDWORD HKCU "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" "EstimatedSize" $0

  ; Only autostart program if in silent mode because GUI has option to launch it anyway
  ${If} ${Silent}
    Call checkLaunchParam
  ${EndIf}
SectionEnd

;--------------------------------


Section "Uninstall"
  ; Remove program
  Delete "$INSTDIR\${PRODUCT}.exe"

  ; Remove shortcuts
  Delete "$SMPROGRAMS\${PRODUCT}.lnk"
  Delete "$DESKTOP\${PRODUCT}.lnk"

  ; Remove registry keys
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Run\${PRODUCT}"
  DeleteRegKey HKCU "SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\${PRODUCT}.exe"
  DeleteRegKey HKCU "SOFTWARE\Classes\${PRODUCT}"
  DeleteRegKey HKCU "SOFTWARE\Classes\Applications\${PRODUCT}.exe"
  DeleteRegValue HKCU "SOFTWARE\RegisteredApplications" "${PRODUCT}"

  ; Remove uninstaller
  DeleteRegKey HKCU "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}"
  Delete "$INSTDIR\${PRODUCT}_uninstall.exe"

  RMDir /r "$INSTDIR"
SectionEnd
