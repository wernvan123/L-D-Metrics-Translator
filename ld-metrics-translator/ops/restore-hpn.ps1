param(
  [Parameter(Mandatory=$true)]
  [string]$BackupFile
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot ".."))
$targetDb = Join-Path $repoRoot "app.db"

if (!(Test-Path $BackupFile)) {
  throw "Backup file not found: $BackupFile"
}

if (Test-Path $targetDb) {
  $ts = Get-Date -Format "yyyyMMdd_HHmmss"
  Copy-Item $targetDb "$targetDb.pre_restore_$ts" -Force
}

Copy-Item $BackupFile $targetDb -Force

Write-Host "Restore complete"
Write-Host " Target DB: $targetDb"
Write-Host "Next: start the app (after setting SECRET_KEY) with: python run.py"
