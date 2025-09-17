import sqlite3
from datetime import datetime

DB_PATH = r"ld-metrics-translator/app.db"

ROLES = [
    {
        "name": "L&D Analyst",
        "department": "Learning & Development",
        "description": "Analyzes learning data and outcomes to inform strategy.",
        "knowledge": [
            "Learning Theories",
            "Assessment Design",
            "Basic Statistics",
        ],
        "skills": [
            "Data Analysis",
            "Stakeholder Communication",
        ],
        "abilities": [
            "Analytical Thinking",
            "Problem Solving",
        ],
        "others": [
            "SQL or BI Tool Experience",
        ],
    },
    {
        "name": "Shift Supervisor",
        "department": "Operations",
        "description": "Supervises shift operations, ensuring quality and safety.",
        "knowledge": [
            "Safety Standards",
            "Process KPIs",
        ],
        "skills": [
            "Coaching",
            "Performance Feedback",
        ],
        "abilities": [
            "Decision Making Under Pressure",
        ],
        "others": [
            "Shift Work Availability",
        ],
    },
]

CREATE_TABLES_SQL = [
    # Minimal schema (compatible superset for dev); if tables exist, these are no-ops under SQLite when guarded
    """
    CREATE TABLE IF NOT EXISTS role_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT,
        department TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_date TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS role_knowledge (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role_profile_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        FOREIGN KEY(role_profile_id) REFERENCES role_profiles(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS role_skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role_profile_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        FOREIGN KEY(role_profile_id) REFERENCES role_profiles(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS role_abilities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role_profile_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        FOREIGN KEY(role_profile_id) REFERENCES role_profiles(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS role_other_requirements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role_profile_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        FOREIGN KEY(role_profile_id) REFERENCES role_profiles(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS competencies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        framework_id INTEGER,
        name TEXT NOT NULL,
        slug TEXT NOT NULL,
        description TEXT,
        sort_order INTEGER DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS role_competency_targets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role_profile_id INTEGER NOT NULL,
        competency_id INTEGER NOT NULL,
        target_level INTEGER NOT NULL DEFAULT 3,
        weight REAL DEFAULT 1.0,
        FOREIGN KEY(role_profile_id) REFERENCES role_profiles(id) ON DELETE CASCADE
    )
    """,
]


def upsert_role(cur, name, department, description, now):
    row = cur.execute("SELECT id FROM role_profiles WHERE name = ?", (name,)).fetchone()
    if row:
        cur.execute(
            "UPDATE role_profiles SET department=?, description=?, is_active=1 WHERE id=?",
            (department, description, row[0]),
        )
        return row[0]
    cur.execute(
        "INSERT INTO role_profiles (name, department, description, is_active, created_date) VALUES (?, ?, ?, 1, ?)",
        (name, department, description, now),
    )
    return cur.lastrowid


def insert_items(cur, table, role_id, items):
    cur.execute(f"DELETE FROM {table} WHERE role_profile_id = ?", (role_id,))
    for it in items:
        if not it:
            continue
        cur.execute(
            f"INSERT INTO {table} (role_profile_id, name) VALUES (?, ?)",
            (role_id, it),
        )


def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    for sql in CREATE_TABLES_SQL:
        cur.execute(sql)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    created = 0
    for role in ROLES:
        rid = upsert_role(cur, role["name"], role.get("department"), role.get("description"), now)
        insert_items(cur, "role_knowledge", rid, role.get("knowledge", []))
        insert_items(cur, "role_skills", rid, role.get("skills", []))
        insert_items(cur, "role_abilities", rid, role.get("abilities", []))
        insert_items(cur, "role_other_requirements", rid, role.get("others", []))
        created += 1

    con.commit()
    total = cur.execute("SELECT COUNT(*) FROM role_profiles").fetchone()[0]
    print(f"Seeded/updated {created} roles. Total roles: {total}")
    con.close()


if __name__ == "__main__":
    main()
