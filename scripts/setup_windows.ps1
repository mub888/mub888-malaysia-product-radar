$ErrorActionPreference = "Stop"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python is not available in PATH. Install Python 3.12+ and try again."
}

python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host "Opening your installed Google Chrome with a dedicated MarketWeb profile..."
$env:RADAR_BROWSER_PROFILE = Join-Path $PSScriptRoot "..\MarketWeb\chrome-profile"
$env:RADAR_MODE = "direct"
& .\.venv\Scripts\python.exe -m radar login

Write-Host "Setup complete. Run scripts\run_now.ps1 for the first live collection."
