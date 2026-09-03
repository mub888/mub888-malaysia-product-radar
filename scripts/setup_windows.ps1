$ErrorActionPreference = "Stop"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python is not available in PATH. Install Python 3.12+ and try again."
}

python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

$projectRoot = Split-Path -Parent $PSScriptRoot
$profilePath = Join-Path $projectRoot "MarketWeb\chrome-profile"
$chromeCandidates = @(
    (Join-Path $env:ProgramFiles "Google\Chrome\Application\chrome.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Google\Chrome\Application\chrome.exe"),
    (Join-Path $env:LOCALAPPDATA "Google\Chrome\Application\chrome.exe")
)
$chromePath = $chromeCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $chromePath) {
    throw "Regular Google Chrome was not found. Install Google Chrome, then run this setup again."
}

New-Item -ItemType Directory -Force -Path $profilePath | Out-Null
Write-Host "Opening regular Google Chrome with the dedicated MarketWeb profile..."
Start-Process -FilePath $chromePath -ArgumentList @(
    "--user-data-dir=$profilePath",
    "https://shop.tiktok.com/",
    "https://www.lazada.com.my/",
    "https://shopee.com.my/"
)
Read-Host "Complete any normal login/region prompts in Chrome, close the MarketWeb Chrome window, then press Enter here"

Write-Host "Setup complete. Run scripts\run_now.ps1 for the first live collection."
