import sqlite3
from datetime import datetime

DB_PATH = r"ld-metrics-translator/app.db"

METRIC_TYPES = [
    ("Efficiency", "Operational efficiency of L&D (cost, time, throughput)", "Operations", "#2d89ef", "speedometer", 10),
    ("Effectiveness", "Learning effectiveness and knowledge/skill attainment", "Learning", "#9f00a7", "target", 20),
    ("Adoption", "Usage, engagement, participation", "Engagement", "#00a300", "users", 30),
    ("Impact", "Business outcomes and behavioral change", "Outcomes", "#e3a21a", "trending-up", 40),
    ("Financial", "Financial measures including ROI and cost avoidance", "Finance", "#da532c", "dollar-sign", 50),
]

UPSERT = (
    """
    INSERT INTO metric_types (name, description, category, color, icon, sort_order, is_active, created_date)
    VALUES (?, ?, ?, ?, ?, ?, 1, ?)
    ON CONFLICT(name) DO UPDATE SET
        description=excluded.description,
        category=excluded.category,
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
    for name, desc, cat, color, icon, sort in METRIC_TYPES:
        cur.execute(UPSERT, (name, desc, cat, color, icon, sort, now))
    con.commit()

    total = cur.execute("SELECT COUNT(*) FROM metric_types").fetchone()[0]
    print("Metric types total:", total)
    for row in cur.execute("SELECT name FROM metric_types ORDER BY sort_order, name").fetchall():
        print(" -", row[0])
    con.close()

if __name__ == '__main__':
    main()
