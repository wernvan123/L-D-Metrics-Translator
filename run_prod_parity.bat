@echo off
REM Start the app in PRODUCTION PARITY mode (Mocks OFF)
set USE_MOCKS=false
set FLASK_DEBUG=0

REM Set upstreams ONLY for endpoints you have ready in your backend.
REM If an upstream is not set, that endpoint will be unavailable (404), matching production.
REM Example:
REM set CONTEXT_STATE_UPSTREAM=https://your-backend/api/context/framework/state
REM set CONTEXT_SYSTEM_UPSTREAM=https://your-backend/api/context/system
REM set CONTEXT_METRICS_SELECT_UPSTREAM=https://your-backend/api/context/metrics/select
REM set CONTEXT_FRAMEWORK_COMPETENCIES_UPSTREAM=https://your-backend/api/context/framework/competencies
REM set FRAMEWORKS_TREE_UPSTREAM=https://your-backend/api/frameworks/{framework_id}/tree
REM set SMART_RECS_GENERATE_UPSTREAM=https://your-backend/api/smart-recommendations/generate
REM set SMART_RECS_INTERACT_UPSTREAM=https://your-backend/api/smart-recommendations/interact
REM set DYNAMIC_REPORTS_START_UPSTREAM=https://your-backend/api/dynamic-reports
REM set DYNAMIC_REPORTS_STATUS_UPSTREAM=https://your-backend/api/dynamic-reports/{job_id}/status

python app.py
