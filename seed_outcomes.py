import sqlite3
from datetime import datetime

DB_PATH = r"ld-metrics-translator/app.db"

OUTCOMES = [
    ("Knowledge Gain", "Increase in knowledge as measured by assessments", "Learning", "Level 2", "#4b9cd3", "book", 10),
    ("Skill Acquisition", "Development of practical skills and proficiency", "Learning", "Level 2", "#7a52c1", "toolbox", 20),
    ("Behavior Change", "Application of learning on the job", "Behavior", "Level 3", "#2e7d32", "handshake", 30),
    ("Performance Improvement", "Improved individual performance metrics", "Outcomes", "Level 4", "#ff9800", "trending-up", 40),
    ("Productivity", "Increased throughput or reduced cycle time", "Outcomes", "Level 4", "#607d8b", "timer", 50),
    ("Quality", "Reduction in errors and improved quality", "Outcomes", "Level 4", "#795548", "check-circle", 60),
    ("Compliance", "Improved adherence to regulations and policies", "Outcomes", "Level 4", "#9e9e9e", "shield", 70),
    ("Engagement", "Higher learner or employee engagement levels", "Engagement", "Level 1", "#3f51b5", "smile", 80),
    ("Retention", "Improved employee retention and reduced turnover", "People", "Level 4", "#009688", "users", 90),
    ("ROI", "Financial return on L&D investments", "Finance", "Level 5", "#d32f2f", "dollar-sign", 100),
]

UPSERT = (
    """
    INSERT INTO ld_outcomes (name, description, category, level, color, icon, sort_order, is_active, created_date)
    VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
    ON CONFLICT(name) DO UPDATE SET
        description=excluded.description,
        category=excluded.category,
        level=excluded.level,
        color=excluded.color,
        icon=excluded.icon,
        sort_order=excluded.sort_order,
        is_active=1
    """
)

def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for name, desc, cat, level, color, icon, sort in OUTCOMES:
        cur.execute(UPSERT, (name, desc, cat, level, color, icon, sort, now))
    con.commit()

    total = cur.execute("SELECT COUNT(*) FROM ld_outcomes").fetchone()[0]
    print("Outcomes total:", total)
    for row in cur.execute("SELECT name FROM ld_outcomes ORDER BY sort_order, name").fetchall():
        print(" -", row[0])
    con.close()

if __name__ == '__main__':
    main()
