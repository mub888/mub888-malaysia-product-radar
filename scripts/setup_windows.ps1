$ErrorActionPreference = "Stop"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python is not available in PATH. Install Python 3.12+ and try again."
}

python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m playwright install chromium

Write-Host "Opening normal browser pages for first-time login/region confirmation..."
$env:RADAR_MODE = "direct"
& .\.venv\Scripts\python.exe -m radar login

Write-Host "Setup complete. Run scripts\run_now.ps1 for the first live collection."
