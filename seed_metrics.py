import sqlite3
from datetime import datetime

DB_PATH = r"ld-metrics-translator/app.db"

# name, description, outcome_name, metric_type_name, measurement_method, unit, freq, example
METRICS = [
    (
        "Post-Training Knowledge Test Score",
        "Average score on post-training assessments to measure knowledge gain.",
        "Knowledge Gain",
        "Effectiveness",
        "Standardized multiple-choice or scenario-based assessment",
        "percentage",
        "per course",
        "Average score ≥ 85% across cohorts",
    ),
    (
        "Skills Proficiency Assessment",
        "Observed or simulated performance rating against skill rubric.",
        "Skill Acquisition",
        "Effectiveness",
        "Rubric-based observation or simulation scoring",
        "score",
        "quarterly",
        "≥ 4/5 proficiency within 60 days post training",
    ),
    (
        "On-the-Job Behavior Adoption",
        "Percentage of employees consistently applying the target behavior at work.",
        "Behavior Change",
        "Impact",
        "Manager check-ins / 360 / system logs",
        "percentage",
        "monthly",
        ">= 70% adoption within 90 days",
    ),
    (
        "Productivity Improvement",
        "Change in throughput or cycle time for target process post training.",
        "Productivity",
        "Impact",
        "Process KPIs (system telemetry)",
        "percent_change",
        "monthly",
        "≥ 15% improvement vs baseline",
    ),
    (
        "Quality Defect Rate",
        "Reduction in errors/defects related to trained competencies.",
        "Quality",
        "Impact",
        "Quality audits / defect tracking",
        "percent_change",
        "monthly",
        "≤ -20% defect rate within 3 months",
    ),
    (
        "Learner Satisfaction (CSAT)",
        "Average satisfaction score from learners (Level 1).",
        "Engagement",
        "Adoption",
        "Post-event survey (Likert 1-5)",
        "score",
        "per event",
        ">= 4.5/5 satisfaction",
    ),
    (
        "Training Completion Rate",
        "Percentage of enrolled learners who complete the training.",
        "Engagement",
        "Adoption",
        "LMS completion data",
        "percentage",
        "weekly",
        ">= 90% completion",
    ),
    (
        "Compliance Pass Rate",
        "Percentage of employees passing mandatory compliance assessments.",
        "Compliance",
        "Effectiveness",
        "Compliance assessment results",
        "percentage",
        "monthly",
        ">= 98% pass rate",
    ),
    (
        "Training ROI",
        "Financial return from L&D initiative relative to costs.",
        "ROI",
        "Financial",
        "(Net Benefits - Cost) / Cost",
        "ratio",
        "quarterly",
        ">= 1.5 ROI within 12 months",
    ),
]

INSERT_SQL = (
    """
    INSERT INTO metrics (
        name, description, outcome_id, metric_type_id, measurement_method, data_source, frequency,
        unit_of_measure, example, data_collection, success_criteria, is_active, created_date
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
    """
)

FIND_OUTCOME = "SELECT id FROM ld_outcomes WHERE name = ?"
FIND_TYPE = "SELECT id FROM metric_types WHERE name = ?"


def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Build name->id maps
    outcomes = {name: _id for (_id, name) in cur.execute("SELECT id, name FROM ld_outcomes").fetchall()}
    types = {name: _id for (_id, name) in cur.execute("SELECT id, name FROM metric_types").fetchall()}

    inserted = 0
    for name, desc, outcome_name, type_name, method, unit, freq, success in METRICS:
        outcome_id = outcomes.get(outcome_name)
        type_id = types.get(type_name)
        if not (outcome_id and type_id):
            print(f"[skip] Missing foreign keys for metric '{name}' (outcome={outcome_name} type={type_name})")
            continue
        # Upsert by unique (name). If not unique, emulate by check-then-insert/update.
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
        else:
            cur.execute(
                INSERT_SQL,
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
            inserted += 1

    con.commit()

    total = cur.execute("SELECT COUNT(*) FROM metrics").fetchone()[0]
    print(f"Inserted {inserted} new metrics. Metrics total: {total}")

    con.close()


if __name__ == '__main__':
    main()
