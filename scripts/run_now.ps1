$ErrorActionPreference = "Stop"
$env:RADAR_MODE = "direct"
$env:RADAR_HEADLESS = "false"
$env:RADAR_BROWSER_PROFILE = Join-Path $PSScriptRoot "..\MarketWeb\chrome-profile"
& .\.venv\Scripts\python.exe -m radar
