$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$port = if ($env:PORT) { [int]$env:PORT } else { 8090 }
$existing = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    $processId = $existing.OwningProcess | Select-Object -First 1
    Write-Host "Stopping process on port $port (PID $processId)..." -ForegroundColor Yellow
    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
}

$env:PORT = $port
Write-Host "Starting DSNS PDF Pro on http://127.0.0.1:$port" -ForegroundColor Green
py app.py