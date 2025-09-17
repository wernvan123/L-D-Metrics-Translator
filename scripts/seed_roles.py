import sqlite3
from datetime import datetime
from typing import List, Tuple, Optional

DB_PATH = r"ld-metrics-translator/app.db"
NOW = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

ROLES = [
    {
        "name": "Shift Supervisor",
        "department": "Operations",
        "description": "Frontline leader coordinating shifts, ensuring safety, quality and throughput.",
        "knowledge": [
            "Safety procedures",
            "Work instructions",
            "Incident reporting"
        ],
        "skills": [
            "Team communication",
            "Prioritization",
            "Conflict resolution"
        ],
        "abilities": [
            "Situational awareness",
            "Decision-making under pressure"
        ],
        "others": [
            "First Aid (preferred)",
            "Forklift certification (where applicable)"
        ],
        # Will try to map to existing competencies by name (case-insensitive)
        "targets": [
            ("Communication", 3, 1.0),
            ("Coaching", 3, 1.0),
            ("Self-Management", 3, 1.0),
        ],
    },
    {
        "name": "L&D Analyst",
        "department": "Learning & Development",
        "description": "Analyzes training effectiveness and supports program optimization.",
        "knowledge": [
            "Learning analytics",
            "Survey design",
            "Data privacy"
        ],
        "skills": [
            "Data analysis",
            "Stakeholder communication",
            "Report writing"
        ],
        "abilities": [
            "Critical thinking",
            "Problem solving"
        ],
        "others": [
            "Excel/Sheets proficiency",
            "BI tool familiarity"
        ],
        "targets": [
            ("Self-Awareness", 3, 1.0),
            ("Relationship Management", 3, 0.8),
        ],
    }
]


def ensure_tables(conn: sqlite3.Connection) -> None:
    """Best-effort create tables if they don't exist (for dev environments)."""
    c = conn.cursor()
    # role_profiles
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS role_profiles (
            id INTEGER PRIMARY KEY,
            name VARCHAR(200) NOT NULL UNIQUE,
            description TEXT,
            department VARCHAR(200),
            is_active BOOLEAN NOT NULL DEFAULT 1,
            created_date DATETIME NOT NULL
        )
        """
    )
    # KSAO tables
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS role_knowledge (
            id INTEGER PRIMARY KEY,
            role_profile_id INTEGER NOT NULL,
            name VARCHAR(300) NOT NULL,
            description TEXT,
            FOREIGN KEY(role_profile_id) REFERENCES role_profiles(id) ON DELETE CASCADE
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS role_skills (
            id INTEGER PRIMARY KEY,
            role_profile_id INTEGER NOT NULL,
            name VARCHAR(300) NOT NULL,
            description TEXT,
            FOREIGN KEY(role_profile_id) REFERENCES role_profiles(id) ON DELETE CASCADE
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS role_abilities (
            id INTEGER PRIMARY KEY,
            role_profile_id INTEGER NOT NULL,
            name VARCHAR(300) NOT NULL,
            description TEXT,
            FOREIGN KEY(role_profile_id) REFERENCES role_profiles(id) ON DELETE CASCADE
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS role_other_requirements (
            id INTEGER PRIMARY KEY,
            role_profile_id INTEGER NOT NULL,
            name VARCHAR(300) NOT NULL,
            description TEXT,
            FOREIGN KEY(role_profile_id) REFERENCES role_profiles(id) ON DELETE CASCADE
        )
        """
    )
    # targets
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS role_competency_targets (
            id INTEGER PRIMARY KEY,
            role_profile_id INTEGER NOT NULL,
            competency_id INTEGER NOT NULL,
            target_level INTEGER NOT NULL DEFAULT 3,
            weight FLOAT DEFAULT 1.0,
            FOREIGN KEY(role_profile_id) REFERENCES role_profiles(id) ON DELETE CASCADE
        )
        """
    )
    conn.commit()


def get_competency_id_by_name(conn: sqlite3.Connection, name: str) -> Optional[int]:
    c = conn.cursor()
    c.execute("SELECT id FROM competencies WHERE lower(name) = lower(?)", (name.strip(),))
    row = c.fetchone()
    return int(row[0]) if row else None


def upsert_role(conn: sqlite3.Connection, name: str, description: str, department: str) -> int:
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO role_profiles (name, description, department, is_active, created_date)
        VALUES (?, ?, ?, 1, ?)
        ON CONFLICT(name) DO UPDATE SET
            description = excluded.description,
            department = excluded.department,
            is_active = 1
        """,
        (name, description, department, NOW),
    )
    conn.commit()
    c.execute("SELECT id FROM role_profiles WHERE name = ?", (name,))
    rid = c.fetchone()
    return int(rid[0])


def replace_ksao(conn: sqlite3.Connection, role_id: int, table: str, names: List[str]) -> None:
    c = conn.cursor()
    c.execute(f"DELETE FROM {table} WHERE role_profile_id = ?", (role_id,))
    for nm in names:
        nm = (nm or '').strip()
        if not nm:
            continue
        c.execute(
            f"INSERT INTO {table} (role_profile_id, name, description) VALUES (?, ?, ?)",
            (role_id, nm, None),
        )
    conn.commit()


def replace_targets(conn: sqlite3.Connection, role_id: int, targets: List[Tuple[str, int, float]]) -> int:
    c = conn.cursor()
    c.execute("DELETE FROM role_competency_targets WHERE role_profile_id = ?", (role_id,))
    added = 0
    for (comp_name, level, weight) in targets:
        cid = get_competency_id_by_name(conn, comp_name)
        if cid is None:
            # try fuzzy fallback: first competency matching prefix
            c2 = conn.cursor()
            c2.execute("SELECT id FROM competencies WHERE lower(name) LIKE ? ORDER BY name LIMIT 1", (f"{comp_name.strip().lower()}%",))
            r2 = c2.fetchone()
            cid = int(r2[0]) if r2 else None
        if cid is None:
            continue
        try:
            c.execute(
                """
                INSERT INTO role_competency_targets (role_profile_id, competency_id, target_level, weight)
                VALUES (?, ?, ?, ?)
                """,
                (role_id, cid, int(level or 3), float(weight or 1.0)),
            )
            added += 1
        except Exception:
            # ignore duplicates or constraint issues silently for seeding
            pass
    conn.commit()
    return added


def main():
    con = sqlite3.connect(DB_PATH)
    ensure_tables(con)

    total_roles = 0
    total_targets = 0

    for r in ROLES:
        rid = upsert_role(con, r["name"], r.get("description") or "", r.get("department") or "")
        replace_ksao(con, rid, "role_knowledge", r.get("knowledge") or [])
        replace_ksao(con, rid, "role_skills", r.get("skills") or [])
        replace_ksao(con, rid, "role_abilities", r.get("abilities") or [])
        replace_ksao(con, rid, "role_other_requirements", r.get("others") or [])
        added = replace_targets(con, rid, r.get("targets") or [])
        total_roles += 1
        total_targets += added
        print(f"Seeded role '{r['name']}' (id={rid}) with {added} targets")

    # Summary
    c = con.cursor()
    cnt_roles = c.execute("SELECT COUNT(*) FROM role_profiles").fetchone()[0]
    print(f"Done. Seeded/updated {total_roles} roles. DB now has {cnt_roles} role_profiles. Targets inserted this run: {total_targets}")

    con.close()


if __name__ == "__main__":
    main()
