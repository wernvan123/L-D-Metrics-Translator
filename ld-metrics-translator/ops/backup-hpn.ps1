param(
  [string]$LocalRoot = "C:\HPN-Backups\local",
  [string]$ExternalRoot = "D:\HPN-Backups",
  [int]$KeepLocal = 48,
  [int]$KeepExternal = 48,
  [switch]$IncludeReports
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot ".."))
$sourceDb = Join-Path $repoRoot "app.db"

if (!(Test-Path $sourceDb)) {
  throw "DB not found at: $sourceDb"
}

New-Item -ItemType Directory -Force -Path $LocalRoot | Out-Null
New-Item -ItemType Directory -Force -Path $ExternalRoot | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$destLocal = Join-Path $LocalRoot "app_$timestamp.db"
$destExternal = Join-Path $ExternalRoot "app_$timestamp.db"

Copy-Item -Path $sourceDb -Destination $destLocal -Force
Copy-Item -Path $sourceDb -Destination $destExternal -Force

if ($IncludeReports) {
  $reportDirs = @(
    (Join-Path $repoRoot "static\reports"),
    (Join-Path $repoRoot "app\static\reports")
  )
  foreach ($d in $reportDirs) {
    if (Test-Path $d) {
      $name = Split-Path $d -Leaf
      $outLocal = Join-Path $LocalRoot "reports_$timestamp"
      $outExternal = Join-Path $ExternalRoot "reports_$timestamp"
      New-Item -ItemType Directory -Force -Path $outLocal | Out-Null
      New-Item -ItemType Directory -Force -Path $outExternal | Out-Null
      Copy-Item -Path (Join-Path $d "*") -Destination $outLocal -Recurse -Force -ErrorAction SilentlyContinue
      Copy-Item -Path (Join-Path $d "*") -Destination $outExternal -Recurse -Force -ErrorAction SilentlyContinue
    }
  }
}

Get-ChildItem $LocalRoot -Filter "app_*.db" | Sort-Object LastWriteTime -Descending | Select-Object -Skip $KeepLocal | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem $ExternalRoot -Filter "app_*.db" | Sort-Object LastWriteTime -Descending | Select-Object -Skip $KeepExternal | Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host "Backup complete"
Write-Host " Local:    $destLocal"
Write-Host " External: $destExternal"
