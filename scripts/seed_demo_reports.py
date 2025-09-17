import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join('ld-metrics-translator', 'app.db')

DDL_REPORT_TEMPLATES = """
CREATE TABLE IF NOT EXISTS report_templates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  description TEXT,
  template_type TEXT,
  created_by TEXT,
  is_active INTEGER DEFAULT 1,
  created_date TEXT
);
"""

DDL_DYNAMIC_REPORTS = """
CREATE TABLE IF NOT EXISTS dynamic_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  template_id INTEGER NOT NULL,
  session_id TEXT NOT NULL,
  selected_outcomes TEXT,
  selected_metrics TEXT,
  generation_status TEXT,
  result_summary TEXT,
  error_message TEXT,
  created_date TEXT NOT NULL,
  generated_date TEXT,
  FOREIGN KEY(template_id) REFERENCES report_templates(id)
);
"""

def _columns(cur, table):
    cur.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]

def seed():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    # Ensure tables exist (best-effort, compatible with migrations)
    cur.execute(DDL_REPORT_TEMPLATES)
    cur.execute(DDL_DYNAMIC_REPORTS)

    # Ensure required columns exist on dynamic_reports (in case of older local schema)
    dyn_cols = set(_columns(cur, 'dynamic_reports'))
    for coldef in [
        ('result_summary', 'TEXT'),
        ('error_message', 'TEXT'),
        ('selected_outcomes', 'TEXT'),
        ('selected_metrics', 'TEXT'),
        ('generated_date', 'TEXT'),
        ('generation_progress', 'INTEGER DEFAULT 0'),
        ('download_count', 'INTEGER DEFAULT 0'),
        ('pdf_path', 'TEXT'),
        ('ai_recommendations', 'TEXT'),
        ('generation_context', 'TEXT'),
        ('executive_summary', 'TEXT'),
        ('strategy_context', 'TEXT'),
        ('metric_analysis', 'TEXT'),
        ('ai_insights', 'TEXT'),
        ('implementation_roadmap', 'TEXT'),
        ('success_metrics', 'TEXT'),
        ('appendices', 'TEXT'),
    ]:
        name, typ = coldef
        if name not in dyn_cols:
            try:
                cur.execute(f"ALTER TABLE dynamic_reports ADD COLUMN {name} {typ}")
            except sqlite3.OperationalError:
                pass

    # Insert a default template if none exists
    cur.execute("SELECT id FROM report_templates LIMIT 1")
    row = cur.fetchone()
    if row:
        template_id = row[0]
    else:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute(
            "INSERT INTO report_templates (name, description, template_type, created_by, is_active, created_date) VALUES (?,?,?,?,?,?)",
            ("Standard Plan Template", "Default template for demo reports", "plan", "system", 1, now)
        )
        template_id = cur.lastrowid

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    session_id = 'demo-session'

    # Build payloads and insert only columns that exist
    dyn_cols = set(_columns(cur, 'dynamic_reports'))
    base_rows = [
        {
            'title': 'Plan Builder Report – Demo A',
            'template_id': template_id,
            'session_id': session_id,
            'generation_status': 'completed',
            'generation_progress': 100,
            'download_count': 0,
            'result_summary': 'Summary of selected competencies and targets.',
            'created_date': now,
            'generated_date': now,
            'selected_outcomes': None,
            'selected_metrics': None,
            'estimated_pages': None,
            'pdf_path': None,
            'ai_recommendations': None,
            'generation_context': None,
            'executive_summary': None,
            'strategy_context': None,
            'metric_analysis': None,
            'ai_insights': None,
            'implementation_roadmap': None,
            'success_metrics': None,
            'appendices': None,
        },
        {
            'title': 'Diagnostics Report – Demo B',
            'template_id': template_id,
            'session_id': session_id,
            'generation_status': 'completed',
            'generation_progress': 100,
            'download_count': 0,
            'result_summary': 'Analysis of recent diagnostic inputs.',
            'created_date': now,
            'generated_date': now,
            'selected_outcomes': None,
            'selected_metrics': None,
            'estimated_pages': None,
            'pdf_path': None,
            'ai_recommendations': None,
            'generation_context': None,
            'executive_summary': None,
            'strategy_context': None,
            'metric_analysis': None,
            'ai_insights': None,
            'implementation_roadmap': None,
            'success_metrics': None,
            'appendices': None,
        },
        {
            'title': 'L&D Summary – Demo C',
            'template_id': template_id,
            'session_id': session_id,
            'generation_status': 'in_progress',
            'generation_progress': 30,
            'download_count': 0,
            'result_summary': 'Generating... please wait.',
            'created_date': now,
            'generated_date': None,
            'selected_outcomes': None,
            'selected_metrics': None,
            'estimated_pages': None,
            'pdf_path': None,
            'ai_recommendations': None,
            'generation_context': None,
            'executive_summary': None,
            'strategy_context': None,
            'metric_analysis': None,
            'ai_insights': None,
            'implementation_roadmap': None,
            'success_metrics': None,
            'appendices': None,
        },
    ]

    inserted = 0
    for payload in base_rows:
        # Filter payload by existing columns
        cols = [k for k in payload.keys() if k in dyn_cols]
        placeholders = ','.join(['?'] * len(cols))
        sql = f"INSERT INTO dynamic_reports ({','.join(cols)}) VALUES ({placeholders})"
        cur.execute(sql, tuple(payload[c] for c in cols))
        inserted += 1

    con.commit()
    con.close()
    print(f'Seeded {inserted} demo reports into {DB_PATH}')

if __name__ == '__main__':
    seed()
