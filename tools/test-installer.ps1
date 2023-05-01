param ([String]$confirm='n')

$ErrorActionPreference = "Stop"

Write-Warning "This script will mess up your existing RestoreWindowPos install."
Write-Warning "Do not run this script except for testing/development purposes"
if ($confirm -ne 'y') {
    $confirm = Read-Host "Are you Sure You Want To Proceed?"
    if ($confirm -ne 'y') {
        exit 1
    }
}

# AppData includes Roaming. Escape to parent
$INSTALL_DIR="$env:AppData\..\Local\Programs\RestoreWindowPos"

function TestPostInstall {
    if (!(Test-Path $INSTALL_DIR)) {
        Write-Error "program not installed"
    } elseif (!(Test-Path "$INSTALL_DIR\RestoreWindowPos.exe")) {
        Write-Error "main executable not installed"
    } elseif (!(Test-Path "$INSTALL_DIR\RestoreWindowPos_uninstall.exe")) {
        Write-Error "uninstaller not installed"
    } else {
        return
    }
    exit 1
}

function GetLastAccess {
    return (Get-ChildItem $INSTALL_DIR -rec | Where-Object {
        $_.Name -match 'RestoreWindowPos.*\.exe$'
    } | Select-Object FullName, LastAccessTime)
}

function DoInstallRWP {
    choco install restorewindowpos -s dist -y -f
    TestPostInstall
}

function DoUpgradeRWP {
    param ($ExtraParams)
    $lastaccess=$(GetLastAccess)
    Invoke-Expression "choco upgrade restorewindowpos -s dist -y -f $ExtraParams"
    TestPostInstall
    $newaccess=$(GetLastAccess)
    $accessdiff=$(Compare-Object -ReferenceObject $lastaccess -DifferenceObject $newaccess -IncludeEqual -ExcludeDifferent)
    if (@($accessdiff).Length -eq 0) {
        Write-Error "upgrade operation did not overwrite installer and uninstaller"
        exit 1
    }
}

function DoUninstallRWP {
    Invoke-Expression "$INSTALL_DIR\RestoreWindowPos_uninstall.exe /S"
    Start-Sleep 3
    if (Test-Path "$INSTALL_DIR\RestoreWindowPos.exe") {
        Write-Error "main executable not uninstalled"
    } elseif (Test-Path "$INSTALL_DIR\RestoreWindowPos_uninstall.exe") {
        Write-Error "uninstaller not uninstalled"
    } else {
        return
    }
    exit 1
}

Write-Warning "Test install"
if (Test-Path ($INSTALL_DIR + "\RestoreWindowPos.exe")) {
    Write-Error "Program is already installed"
    exit 1
}
DoInstallRWP
Write-Warning "Test program has not started after install without being asked"
if ((Get-Process "RestoreWindowPos" -ea SilentlyContinue) -ne $Null) {
    Write-Error "program has been started without asking"
    exit 1
}
Write-Warning "Test program will start after install when asked"
DoUpgradeRWP -ExtraParams "--params '`"/StartAfterInstall`"'"
Start-Sleep 5
if ((Get-Process "RestoreWindowPos" -ea SilentlyContinue) -eq $Null) {
    Write-Error "program did not start after install"
    exit 1
}
Write-Warning "Test we can shut down running instances and still upgrade"
DoUpgradeRWP
if ((Get-Process "RestoreWindowPos" -ea SilentlyContinue) -ne $Null) {
    Write-Error "program was not shut down before install"
    exit 1
}
Write-Warning "Test uninstaller"
DoUninstallRWP
