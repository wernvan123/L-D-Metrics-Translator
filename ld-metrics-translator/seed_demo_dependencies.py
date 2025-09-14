import sqlite3
from datetime import datetime

DB_PATH = r"app.db"

METRIC_TYPES = [
    ("Effectiveness", "Learning effectiveness and knowledge/skill attainment", "Learning", "#9f00a7", "target", 20),
    ("Adoption", "Usage, engagement, participation", "Engagement", "#00a300", "users", 30),
    ("Impact", "Business outcomes and behavioral change", "Outcomes", "#e3a21a", "trending-up", 40),
]

OUTCOMES = [
    ("Engagement", "Higher learner or employee engagement levels", "Engagement", "Level 1", "#3f51b5", "smile", 80),
    ("Productivity", "Increased throughput or reduced cycle time", "Outcomes", "Level 4", "#607d8b", "timer", 50),
    ("Quality", "Reduction in errors and improved quality", "Outcomes", "Level 4", "#795548", "check-circle", 60),
    ("Knowledge Gain", "Increase in knowledge as measured by assessments", "Learning", "Level 2", "#4b9cd3", "book", 10),
]

UPSERT_TYPE = (
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

UPSERT_OUTCOME = (
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

    for name, desc, cat, color, icon, sort in METRIC_TYPES:
        cur.execute(UPSERT_TYPE, (name, desc, cat, color, icon, sort, now))

    for name, desc, cat, level, color, icon, sort in OUTCOMES:
        cur.execute(UPSERT_OUTCOME, (name, desc, cat, level, color, icon, sort, now))

    con.commit()

    # Print quick summaries
    mt_total = cur.execute("SELECT COUNT(*) FROM metric_types").fetchone()[0]
    oc_total = cur.execute("SELECT COUNT(*) FROM ld_outcomes").fetchone()[0]
    print(f"metric_types total: {mt_total}")
    print(f"ld_outcomes total: {oc_total}")

    con.close()


if __name__ == '__main__':
    main()
