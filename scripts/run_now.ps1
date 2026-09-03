$ErrorActionPreference = "Stop"
$env:RADAR_MODE = "direct"
$env:RADAR_HEADLESS = "false"
& .\.venv\Scripts\python.exe -m radar
