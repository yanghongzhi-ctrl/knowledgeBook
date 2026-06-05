param(
  [ValidateSet("ch01", "ch02", "ch03", "ch04", "ch05", "ch06", "ch07", "ch08", "ch09", "ch10", "ch11")]
  [string]$Chapter = "ch05",
  [switch]$Full,
  [switch]$ApplyMigration,
  [int]$DbHybridLimit = 30,
  [string]$DatabaseUrl = "postgresql://postgres@127.0.0.1:55432/road_kb"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$RawDir = Join-Path $Root "data\raw\$Chapter"
$Package = Get-ChildItem -LiteralPath $RawDir -Filter "*.json" -File |
  Select-Object -First 1

if ($null -eq $Package) {
  throw "No knowledge package JSON found in $RawDir"
}

$env:PYTHONPATH = Join-Path $Root "src"
Set-Location $Root

$Args = @(
  "-m", "kb_rag.cli",
  "--package", $Package.FullName,
  "release",
  "--database-url", $DatabaseUrl,
  "--db-hybrid-limit", "$DbHybridLimit"
)

if ($Full) {
  $Args += @("--generate-embeddings", "--apply-db")
}

if ($ApplyMigration) {
  if (-not $Full) {
    throw "-ApplyMigration requires -Full because migration is part of the database release."
  }
  $Args += "--apply-migration"
}

Write-Host "Releasing $Chapter from $($Package.Name)"
if ($Full) {
  Write-Host "Mode: full release with embeddings and PostgreSQL import"
} else {
  Write-Host "Mode: local release check"
}

& py @Args
exit $LASTEXITCODE
