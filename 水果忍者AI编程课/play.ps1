# Fruit Ninja - start local server (PowerShell)
Set-Location $PSScriptRoot
$port = 8123
$url = "http://localhost:$port"

Write-Host ""
Write-Host "========================================"
Write-Host "  Fruit Ninja - Local Server"
Write-Host "  URL: $url"
Write-Host "========================================"
Write-Host ""

$python = $null
if (Get-Command python -ErrorAction SilentlyContinue) { $python = "python" }
elseif (Get-Command py -ErrorAction SilentlyContinue) { $python = "py -3" }

if (-not $python) {
    Write-Host "[ERROR] Python 3 not found." -ForegroundColor Red
    Write-Host "Install from https://www.python.org/downloads/"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Starting server with $python ..."
Start-Process cmd -ArgumentList "/k $python -m http.server $port" -WindowStyle Normal
Start-Sleep -Seconds 2
Start-Process $url
Write-Host ""
Write-Host "Browser opened. Close the server window to stop."
Read-Host "Press Enter to exit"
