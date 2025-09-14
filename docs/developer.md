# Developer Guide

## Data-driven Metric Seeding (Preferred)

Use the JSON-driven seeding to upsert metrics and link them to competencies deterministically.

Files:
- `scripts/data/metrics.json` — list of metrics objects:
  ```json
  {"name": "...", "description": "...", "outcome": "Engagement|Productivity|Retention", "type": "KPI|Behavioral|Assessment"}
  ```
- `scripts/data/competency_metric_map.json` — mapping of `"framework_slug:competency_slug"` → metric names:
  ```json
  {"goleman-emotional-intelligence:self-awareness": ["360 Feedback Score", "Peer Feedback Score"]}
  ```

Run (idempotent):
```powershell
$env:PYTHONPATH="c:\Users\werne\Documents\L & D Metrics Translator - 8\ld-metrics-translator"; python scripts\seed_metrics_from_json.py
```

Notes:
- Uses metric names and framework/competency slugs as natural keys.
- Safe to re-run; updates existing rows and only adds missing links.
- Extend by editing either JSON file and rerun the script.

## Deprecated seeding script

- `scripts/seed_metrics_and_links.py` is deprecated in favor of the JSON-driven flow above and now prints a warning when executed.

## Frontend: Frameworks Browser

- Competency rows display a metric-count badge and lazy-load metrics when clicked.
- After load, counts update automatically to the actual number of linked metrics.
- Files:
  - `ld-metrics-translator/static/js/frameworks.js`
  - `ld-metrics-translator/static/css/style.css` (badge styles under “Frameworks Browser” section)

## Minimal Tab Scaffold

Files:
- `ld-metrics-translator/templates/index.html` — Tab bar and three panels inserted after the hero section (IDs: `#app-tabs`, `#tab-panel-dashboard`, `#tab-panel-plan`, `#tab-panel-analysis`).
- `ld-metrics-translator/static/js/tabs.js` — Hash routing and state handling. Supports `#tab=dashboard|plan|analysis` and `#dashboard|#plan|#analysis`.
- `ld-metrics-translator/static/css/style.css` — Minimal styles under the “Tabs Section (Minimal)” block.
- `ld-metrics-translator/templates/base.html` — Includes tabs.js.

Usage:
- Clicking a tab updates the URL hash (e.g., `#tab=plan`) and toggles the active panel.
- Panels link to existing sections: Dashboard → `#key-numbers`, Plan & Measure → `#explore`, `#implement`, Analysis → `#analyse`.

Debugging:
- A lightweight debug box (`#tabs-debug`) is present; `tabs.js` sets DEBUG=true and writes events there and to the console.
- Unknown tabs fall back to `dashboard` with a debug message.
- If nav/panels are missing, initialization logs a non-fatal message and exits.
