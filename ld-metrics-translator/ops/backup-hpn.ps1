param(
  [string]$LocalRoot = "C:\HPN-Backups\local",
  [string]$ExternalRoot = "D:\HPN-Backups",
  [int]$KeepLocal = 48,
  [int]$KeepExternal = 48,
  [switch]$IncludeReports
)

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

New-Item -ItemType Directory -Force -Path $LocalRoot | Out-Null
$logDir = Join-Path $LocalRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir "backup_$timestamp.log"

$transcriptStarted = $false
try {
  Start-Transcript -Path $logFile -ErrorAction Stop | Out-Null
  $transcriptStarted = $true
} catch {
  Write-Warning "Could not start transcript logging at: $logFile"
}

$ErrorActionPreference = "Stop"

try {
  $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot ".."))
  $sourceDb = Join-Path $repoRoot "app.db"

  if (!(Test-Path $sourceDb)) {
    throw "DB not found at: $sourceDb"
  }

  $externalAvailable = $true
  try {
    New-Item -ItemType Directory -Force -Path $ExternalRoot -ErrorAction Stop | Out-Null
  } catch {
    $externalAvailable = $false
    Write-Warning "External backup location not available (skipping external backup): $ExternalRoot"
  }

  $destLocal = Join-Path $LocalRoot "app_$timestamp.db"
  $destExternal = Join-Path $ExternalRoot "app_$timestamp.db"

  Copy-Item -Path $sourceDb -Destination $destLocal -Force
  if ($externalAvailable) {
    Copy-Item -Path $sourceDb -Destination $destExternal -Force
  }

  if ($IncludeReports) {
    $reportDirs = @(
      (Join-Path $repoRoot "static\reports"),
      (Join-Path $repoRoot "app\static\reports")
    )
    foreach ($d in $reportDirs) {
      if (Test-Path $d) {
        $outLocal = Join-Path $LocalRoot "reports_$timestamp"
        $outExternal = Join-Path $ExternalRoot "reports_$timestamp"
        New-Item -ItemType Directory -Force -Path $outLocal | Out-Null
        if ($externalAvailable) {
          New-Item -ItemType Directory -Force -Path $outExternal | Out-Null
        }
        Copy-Item -Path (Join-Path $d "*") -Destination $outLocal -Recurse -Force -ErrorAction SilentlyContinue
        if ($externalAvailable) {
          Copy-Item -Path (Join-Path $d "*") -Destination $outExternal -Recurse -Force -ErrorAction SilentlyContinue
        }
      }
    }
  }

  Get-ChildItem $LocalRoot -Filter "app_*.db" | Sort-Object LastWriteTime -Descending | Select-Object -Skip $KeepLocal | Remove-Item -Force -ErrorAction SilentlyContinue
  if ($externalAvailable) {
    Get-ChildItem $ExternalRoot -Filter "app_*.db" | Sort-Object LastWriteTime -Descending | Select-Object -Skip $KeepExternal | Remove-Item -Force -ErrorAction SilentlyContinue
  }

  Write-Host "Backup complete"
  Write-Host " Local:    $destLocal"
  if ($externalAvailable) {
    Write-Host " External: $destExternal"
  } else {
    Write-Host " External: SKIPPED (not available)"
  }
  Write-Host " Log:      $logFile"
} catch {
  Write-Error $_
  throw
} finally {
  if ($transcriptStarted) {
    Stop-Transcript | Out-Null
  }
}

