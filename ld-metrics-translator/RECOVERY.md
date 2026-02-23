# Human Performance Navigator (L&D Metrics Translator) — Recovery Runbook (Windows)

## Critical runtime paths (confirmed)
- DB: `C:\Users\werne\OneDrive\Documents\L-D-Metrics-Translator\ld-metrics-translator\app.db`
- Logs: `C:\Users\werne\OneDrive\Documents\L-D-Metrics-Translator\ld-metrics-translator\logs\app.log`

## Preconditions
- You must set `SECRET_KEY` before starting the app.

## Fast backup (recommended after each consulting session)
From `ld-metrics-translator`:

- Backup to local + flash drive (D:):
  - `powershell -ExecutionPolicy Bypass -File .\ops\backup-hpn.ps1`

## Restore database from a backup
From `ld-metrics-translator`:

- `powershell -ExecutionPolicy Bypass -File .\ops\restore-hpn.ps1 -BackupFile "D:\HPN-Backups\app_YYYYMMDD_HHMMSS.db"`

## Catastrophic laptop loss (target RTO ≤ 4 hours)
1. New Windows machine.
2. Install Git and Python.
3. Clone the repo from GitHub.
4. Copy the latest `app_*.db` backup into:
   - `...\ld-metrics-translator\app.db`
5. Set `SECRET_KEY`.
6. Install deps in a venv and start:
   - `python run.py`

## Validation checklist (go/no-go)
- App starts without error.
- Open: `http://localhost:8080/`
- Admin login works.
- Data is present (metrics, roles, event analyses).
