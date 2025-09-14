import sqlite3

DB_PATH = r"ld-metrics-translator/app.db"

# Map metric name -> list of (framework_name, competency_name)
MAPPINGS = {
    "Post-Training Knowledge Test Score": [
        ("Bloom's Taxonomy", "Understand"),
        ("Bloom's Taxonomy", "Apply"),
        ("Kirkpatrick Model", "Learning"),
    ],
    "Skills Proficiency Assessment": [
        ("Bloom's Taxonomy", "Apply"),
        ("ADDIE Model", "Develop"),
    ],
    "On-the-Job Behavior Adoption": [
        ("Kirkpatrick Model", "Behavior"),
        ("OKR Alignment", "Key Results"),
    ],
    "Productivity Improvement": [
        ("Balanced Scorecard (L&D)", "Internal Process"),
        ("CIPP Evaluation Model", "Product"),
    ],
    "Quality Defect Rate": [
        ("Balanced Scorecard (L&D)", "Internal Process"),
    ],
    "Learner Satisfaction (CSAT)": [
        ("Kirkpatrick Model", "Reaction"),
        ("Balanced Scorecard (L&D)", "Customer"),
    ],
    "Training Completion Rate": [
        ("70-20-10 Model", "Formal (10)"),
        ("ADDIE Model", "Implement"),
    ],
    "Compliance Pass Rate": [
        ("Balanced Scorecard (L&D)", "Internal Process"),
    ],
    "Training ROI": [
        ("Phillips ROI Model", "ROI"),
        ("Balanced Scorecard (L&D)", "Financial"),
    ],
}


def get_metric_id(cur, name):
    row = cur.execute("SELECT id FROM metrics WHERE name = ?", (name,)).fetchone()
    return row[0] if row else None


def get_competency_id(cur, framework_name, competency_name):
    fw = cur.execute("SELECT id FROM frameworks WHERE name = ?", (framework_name,)).fetchone()
    if not fw:
        return None
    row = cur.execute(
        "SELECT c.id FROM competencies c WHERE c.framework_id = ? AND c.name = ?",
        (fw[0], competency_name),
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

    created = 0
    skipped = 0
    missing = []

    for metric_name, pairs in MAPPINGS.items():
        m_id = get_metric_id(cur, metric_name)
        if not m_id:
            missing.append(("metric", metric_name))
            continue
        for fw_name, comp_name in pairs:
            c_id = get_competency_id(cur, fw_name, comp_name)
            if not c_id:
                missing.append(("competency", f"{fw_name} / {comp_name}"))
                continue
            if ensure_link(cur, c_id, m_id):
                created += 1
            else:
                skipped += 1

    con.commit()

    print(f"Links created: {created}, existing skipped: {skipped}")
    if missing:
        print("Missing references:")
        for kind, name in missing:
            print(" -", kind, name)

    # Show a quick count
    total = cur.execute("SELECT COUNT(*) FROM competency_metrics").fetchone()[0]
    print("Total competency_metric links:", total)

    con.close()


if __name__ == "__main__":
    main()
