param(
  [int]$ApiPort = 8768,
  [int]$WebPort = 5174,
  [string]$DatabaseUrl = "postgresql://postgres@127.0.0.1:55432/road_kb"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$OutputDir = Join-Path $Root "output"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

function Test-PortListening {
  param([int]$Port)
  $conn = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object { $_.LocalPort -eq $Port } |
    Select-Object -First 1
  return $null -ne $conn
}

function Start-HiddenPowerShell {
  param(
    [string]$Command,
    [string]$LogPath
  )
  Start-Process -FilePath "powershell" -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-Command",
    "$Command *> '$LogPath'"
  ) -WindowStyle Hidden | Out-Null
}

Set-Location $Root

if (-not (Test-PortListening -Port 55432)) {
  Write-Warning "PostgreSQL 55432 is not listening. Start the local PostgreSQL/pgvector runtime before using pgvector mode."
}

if (Test-PortListening -Port $ApiPort) {
  Write-Host "API already listening on http://127.0.0.1:$ApiPort"
} else {
  $apiLog = Join-Path $OutputDir "frontend_api_$ApiPort.log"
  $apiCommand = "`$env:PYTHONPATH='$Root\src'; Set-Location '$Root'; py -m kb_rag.api --port $ApiPort --database-url '$DatabaseUrl'"
  Start-HiddenPowerShell -Command $apiCommand -LogPath $apiLog
  Write-Host "Started API on http://127.0.0.1:$ApiPort"
}

if (Test-PortListening -Port $WebPort) {
  Write-Host "Frontend already listening on http://127.0.0.1:$WebPort/web/"
} else {
  $webLog = Join-Path $OutputDir "frontend_web_$WebPort.log"
  $webCommand = "Set-Location '$Root'; py -m http.server $WebPort --bind 127.0.0.1"
  Start-HiddenPowerShell -Command $webCommand -LogPath $webLog
  Write-Host "Started frontend on http://127.0.0.1:$WebPort/web/"
}

Start-Sleep -Seconds 2
Write-Host ""
Write-Host "Open: http://127.0.0.1:$WebPort/web/"
