import sqlite3
from datetime import datetime

DB_PATH = r"ld-metrics-translator/app.db"

FRAMEWORK_COMPETENCIES = {
    "Kirkpatrick Model": [
        ("Reaction", "reaction", "Level 1: Learner satisfaction and engagement.", 10),
        ("Learning", "learning", "Level 2: Knowledge, skills, attitudes acquired.", 20),
        ("Behavior", "behavior", "Level 3: On-the-job behavior change.", 30),
        ("Results", "results", "Level 4: Organizational impact and results.", 40),
    ],
    "Phillips ROI Model": [
        ("ROI", "roi", "Level 5: Financial return on investment from L&D initiatives.", 10),
    ],
    "CIPP Evaluation Model": [
        ("Context", "context", "Assessment of needs, problems, assets, and opportunities.", 10),
        ("Input", "input", "Strategy, plans, resources to meet program goals.", 20),
        ("Process", "process", "Implementation fidelity and continuous improvement.", 30),
        ("Product", "product", "Outcomes, impacts, effectiveness and sustainability.", 40),
    ],
    "Bloom's Taxonomy": [
        ("Remember", "remember", "Recall facts and basic concepts.", 10),
        ("Understand", "understand", "Explain ideas or concepts.", 20),
        ("Apply", "apply", "Use information in new situations.", 30),
        ("Analyze", "analyze", "Draw connections among ideas.", 40),
        ("Evaluate", "evaluate", "Justify a decision or course of action.", 50),
        ("Create", "create", "Produce new or original work.", 60),
    ],
    "ADDIE Model": [
        ("Analyze", "analyze", "Identify needs, audience, goals, constraints.", 10),
        ("Design", "design", "Blueprint learning objectives, assessments, strategy.", 20),
        ("Develop", "develop", "Produce learning content and assets.", 30),
        ("Implement", "implement", "Deliver training and enablement.", 40),
        ("Evaluate", "evaluate", "Assess effectiveness and improve.", 50),
    ],
    "SAM Model": [
        ("Preparation", "preparation", "Background, outcomes, constraints, stakeholders.", 10),
        ("Iterative Design", "iterative-design", "Rapid prototypes and design iterations.", 20),
        ("Iterative Development", "iterative-development", "Build, test, refine cycles.", 30),
    ],
    "70-20-10 Model": [
        ("Experience (70)", "experience-70", "Experiential learning from challenging assignments.", 10),
        ("Social (20)", "social-20", "Learning from others: coaching, mentoring, feedback.", 20),
        ("Formal (10)", "formal-10", "Structured courses and programs.", 30),
    ],
    "Balanced Scorecard (L&D)": [
        ("Financial", "financial", "Financial perspective: cost, ROI, efficiency.", 10),
        ("Customer", "customer", "Customer perspective: learner satisfaction, stakeholder value.", 20),
        ("Internal Process", "internal-process", "Process perspective: operational excellence, cycle time.", 30),
        ("Learning & Growth", "learning-growth", "Capability perspective: skills, culture, innovation.", 40),
    ],
    "OKR Alignment": [
        ("Objectives", "objectives", "Ambitious qualitative goals that set direction.", 10),
        ("Key Results", "key-results", "Measurable outcomes that indicate success.", 20),
        ("Initiatives", "initiatives", "Activities and projects to achieve KRs.", 30),
    ],
    "Capability Maturity (L&D)": [
        ("Initial", "initial", "Ad hoc, chaotic processes; success depends on individuals.", 10),
        ("Managed", "managed", "Basic project management to track cost, schedule, functionality.", 20),
        ("Defined", "defined", "Processes are documented, standardized, and integrated.", 30),
        ("Quantitatively Managed", "quantitatively-managed", "Processes are measured and controlled.", 40),
        ("Optimizing", "optimizing", "Focus on continuous process improvement.", 50),
    ],
}


def get_framework_id(cur, name: str):
    row = cur.execute("SELECT id FROM frameworks WHERE name = ?", (name,)).fetchone()
    return row[0] if row else None


def upsert_competency(cur, framework_id: int, name: str, slug: str, description: str, sort_order: int):
    # Check if competency exists by framework_id + name
    row = cur.execute(
        "SELECT id FROM competencies WHERE framework_id = ? AND name = ?",
        (framework_id, name),
    ).fetchone()
    if row:
        cur.execute(
            "UPDATE competencies SET slug = ?, description = ?, sort_order = ? WHERE id = ?",
            (slug, description, sort_order, row[0]),
        )
        return "updated"
    else:
        cur.execute(
            "INSERT INTO competencies (framework_id, name, slug, description, sort_order) VALUES (?, ?, ?, ?, ?)",
            (framework_id, name, slug, description, sort_order),
        )
        return "inserted"


def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    total_inserted = 0
    total_updated = 0

    for fw_name, comps in FRAMEWORK_COMPETENCIES.items():
        fw_id = get_framework_id(cur, fw_name)
        if not fw_id:
            print(f"[skip] Framework not found: {fw_name}")
            continue
        inserted = updated = 0
        for name, slug, desc, order in comps:
            res = upsert_competency(cur, fw_id, name, slug, desc, order)
            if res == "inserted":
                inserted += 1
            else:
                updated += 1
        total_inserted += inserted
        total_updated += updated
        count = cur.execute("SELECT COUNT(*) FROM competencies WHERE framework_id = ?", (fw_id,)).fetchone()[0]
        print(f"[ok] {fw_name}: +{inserted} / ~{updated} (total {count})")

    con.commit()

    # Summary
    grand_total = cur.execute("SELECT COUNT(*) FROM competencies").fetchone()[0]
    print(f"Done. Inserted {total_inserted}, updated {total_updated}. Competencies total: {grand_total}")

    con.close()


if __name__ == "__main__":
    main()
