﻿Write-Information "Attempting to kill any running RestoreWindowPos.exe"
taskkill /IM "RestoreWindowPos.exe"
Write-Information "Sleep 2 seconds to make sure process is shut down correctly"
Start-Sleep 2
