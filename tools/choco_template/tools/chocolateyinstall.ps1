$ErrorActionPreference = 'Stop'
$toolsDir   = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"
$fileLocation = Join-Path $toolsDir '[[PackageName]]_install.[[InstallerType]]'

$packageArgs = @{
  packageName   = $env:ChocolateyPackageName
  unzipLocation = $toolsDir
  fileType      = '[[InstallerType]]'
  file         = $fileLocation

  softwareName  = '[[PackageName]]*'

  checksum      = '[[InstallerHash]]'
  checksumType  = 'sha256'

  validExitCodes= @(0)
  silentArgs   = '[[SilentArgs]]'
}

Install-ChocolateyInstallPackage @packageArgs
