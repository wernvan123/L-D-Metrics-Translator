import sqlite3
from datetime import datetime

DB_PATH = r"app.db"

# name, description, outcome_name, metric_type_name, measurement_method, unit, freq, success
METRICS = [
    (
        "360 Feedback Score",
        "Average score from 360 feedback assessments related to EI behaviors.",
        "Engagement",
        "Effectiveness",
        "360 survey instrument",
        "score",
        "quarterly",
        ">= 4.2/5 within 6 months",
    ),
    (
        "Pulse Survey eNPS",
        "Employee Net Promoter Score from quick pulse surveys.",
        "Engagement",
        "Adoption",
        "Pulse survey (single-item eNPS)",
        "score",
        "monthly",
        ">= +30 eNPS",
    ),
    (
        "Time to Productivity",
        "Average time for new or transitioning employees to reach target productivity.",
        "Productivity",
        "Impact",
        "Operational KPI tracking",
        "days",
        "monthly",
        "<= 60 days to target",
    ),
    (
        "Error Rate",
        "Rate of errors or defects in tasks associated with the trained capability.",
        "Quality",
        "Impact",
        "Quality audit / system telemetry",
        "percent_change",
        "monthly",
        "-20% within 3 months",
    ),
    (
        "Coaching Session Completion Rate",
        "Percentage of required coaching sessions completed on time.",
        "Engagement",
        "Adoption",
        "Coaching logs / LMS",
        "percentage",
        "monthly",
        ">= 90% completion",
    ),
    (
        "Learning Retention Score",
        "Average follow-up assessment score 30-60 days post training.",
        "Knowledge Gain",
        "Effectiveness",
        "Follow-up knowledge assessment",
        "percentage",
        "monthly",
        ">= 80% average retention",
    ),
]

# metric -> list of (framework_name, competency_name)
MAPPINGS = {
    "360 Feedback Score": [
        ("Goleman Emotional Intelligence", "Self-Awareness"),
        ("Goleman Emotional Intelligence", "Relationship Management"),
    ],
    "Pulse Survey eNPS": [
        ("Goleman Emotional Intelligence", "Social Awareness"),
        ("Goleman Emotional Intelligence", "Self-Management"),
    ],
    "Time to Productivity": [
        ("Situational Leadership", "Directing"),
        ("Situational Leadership", "Delegating"),
    ],
    "Error Rate": [
        ("Situational Leadership", "Directing"),
        ("Situational Leadership", "Supporting"),
    ],
    "Coaching Session Completion Rate": [
        ("Situational Leadership", "Coaching"),
        ("Goleman Emotional Intelligence", "Relationship Management"),
    ],
    "Learning Retention Score": [
        ("Situational Leadership", "Supporting"),
        ("Goleman Emotional Intelligence", "Self-Management"),
    ],
}

INSERT_METRIC_SQL = (
    """
    INSERT INTO metrics (
        name, description, outcome_id, metric_type_id, measurement_method, data_source, frequency,
        unit_of_measure, example, data_collection, success_criteria, is_active, created_date
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
    """
)


def id_map(cur, table, name_col="name"):
    return {r[1]: r[0] for r in cur.execute(f"SELECT id, {name_col} FROM {table}").fetchall()}


def ensure_metric(cur, now, name, desc, outcome_name, type_name, method, unit, freq, success):
    outcomes = id_map(cur, 'ld_outcomes')
    types = id_map(cur, 'metric_types')
    outcome_id = outcomes.get(outcome_name)
    type_id = types.get(type_name)
    if not outcome_id or not type_id:
        raise RuntimeError(f"Missing FK: outcome={outcome_name} type={type_name}")
    row = cur.execute("SELECT id FROM metrics WHERE name = ?", (name,)).fetchone()
    if row:
        cur.execute(
            """
            UPDATE metrics SET description=?, outcome_id=?, metric_type_id=?, measurement_method=?,
                   unit_of_measure=?, frequency=?, success_criteria=?, is_active=1
            WHERE id=?
            """,
            (desc, outcome_id, type_id, method, unit, freq, success, row[0])
        )
        return row[0], False
    else:
        cur.execute(
            INSERT_METRIC_SQL,
            (
                name,
                desc,
                outcome_id,
                type_id,
                method,
                "LMS / Surveys / Systems",
                freq,
                unit,
                "N/A",
                "Automated / Survey",
                success,
                now,
            ),
        )
        return cur.lastrowid, True


def get_framework_id(cur, name):
    row = cur.execute("SELECT id FROM frameworks WHERE name = ?", (name,)).fetchone()
    return row[0] if row else None


def get_competency_id(cur, framework_id, name):
    row = cur.execute(
        "SELECT id FROM competencies WHERE framework_id = ? AND name = ?",
        (framework_id, name),
    ).fetchone()
    return row[0] if row else None


def ensure_link(cur, competency_id, metric_id):
    row = cur.execute(
        "SELECT 1 FROM competency_metrics WHERE competency_id = ? AND metric_id = ?",
        (competency_id, metric_id),
    ).fetchone()
    if row:
        return False
    cur.execute(
        "INSERT INTO competency_metrics (competency_id, metric_id) VALUES (?, ?)",
        (competency_id, metric_id),
    )
    return True


def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    created = 0
    updated = 0
    links = 0

    ids_by_metric = {}

    for (name, desc, outcome_name, type_name, method, unit, freq, success) in METRICS:
        mid, inserted = ensure_metric(cur, now, name, desc, outcome_name, type_name, method, unit, freq, success)
        ids_by_metric[name] = mid
        if inserted:
            created += 1
        else:
            updated += 1

    # Map metrics to competencies for the two frameworks
    for metric_name, pairs in MAPPINGS.items():
        mid = ids_by_metric.get(metric_name)
        if not mid:
            # metric might pre-exist with different casing; try lookup
            row = cur.execute("SELECT id FROM metrics WHERE name = ?", (metric_name,)).fetchone()
            if not row:
                print(f"[warn] metric not found for mapping: {metric_name}")
                continue
            mid = row[0]
        for fw_name, comp_name in pairs:
            fw_id = get_framework_id(cur, fw_name)
            if not fw_id:
                print(f"[warn] framework not found: {fw_name}")
                continue
            comp_id = get_competency_id(cur, fw_id, comp_name)
            if not comp_id:
                print(f"[warn] competency not found: {fw_name} / {comp_name}")
                continue
            if ensure_link(cur, comp_id, mid):
                links += 1

    con.commit()

    total_metrics = cur.execute("SELECT COUNT(*) FROM metrics").fetchone()[0]
    total_links = cur.execute("SELECT COUNT(*) FROM competency_metrics").fetchone()[0]

    print(f"Metrics created: {created}, updated: {updated}, total metrics: {total_metrics}")
    print(f"New links: {links}, total links: {total_links}")

    con.close()


if __name__ == '__main__':
    main()
