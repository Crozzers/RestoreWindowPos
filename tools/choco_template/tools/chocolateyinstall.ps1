$ErrorActionPreference = 'Stop'
$toolsDir   = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"
$fileLocation = Join-Path $toolsDir 'RestoreWindowPos_install.exe'

$silentArgs = "/S"
$pp = Get-PackageParameters
if ($pp['StartAfterInstall']) {
  $silentArgs += ' /StartAfterInstall'
}
if ($pp['DesktopShortcut']) {
  $silentArgs += ' /DesktopShortcut'
}
if ($pp['StartMenuShortcut']) {
  $silentArgs += ' /StartMenuShortcut'
}

$packageArgs = @{
  packageName   = $env:ChocolateyPackageName
  unzipLocation = $toolsDir
  fileType      = 'exe'
  file         = $fileLocation

  softwareName  = 'RestoreWindowPos*'

  checksum      = '@@InstallerChecksum@@'
  checksumType  = 'sha256'

  validExitCodes= @(0)
  silentArgs   = $silentArgs
}

Install-ChocolateyInstallPackage @packageArgs
