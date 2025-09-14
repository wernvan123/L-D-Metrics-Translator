import sqlite3
from datetime import datetime

DB_PATH = r"ld-metrics-translator/app.db"
NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

FRAMEWORKS = [
    {
        "name": "Kirkpatrick Model",
        "slug": "kirkpatrick-model",
        "description": "Four levels of training evaluation: Reaction, Learning, Behavior, Results.",
        "source": "Donald Kirkpatrick",
        "sort_order": 100,
    },
    {
        "name": "Phillips ROI Model",
        "slug": "phillips-roi-model",
        "description": "Extension of Kirkpatrick adding Level 5: Return on Investment (ROI).",
        "source": "Jack Phillips",
        "sort_order": 110,
    },
    {
        "name": "CIPP Evaluation Model",
        "slug": "cipp-evaluation-model",
        "description": "Context, Input, Process, Product model for program evaluation.",
        "source": "Stufflebeam",
        "sort_order": 120,
    },
    {
        "name": "Bloom's Taxonomy",
        "slug": "blooms-taxonomy",
        "description": "Hierarchy of cognitive learning objectives (Remember–Create).",
        "source": "Benjamin Bloom",
        "sort_order": 130,
    },
    {
        "name": "ADDIE Model",
        "slug": "addie-model",
        "description": "Instructional design process: Analyze, Design, Develop, Implement, Evaluate.",
        "source": "Instructional Design",
        "sort_order": 140,
    },
    {
        "name": "SAM Model",
        "slug": "sam-model",
        "description": "Successive Approximation Model: iterative, agile instructional design.",
        "source": "Allen Interactions",
        "sort_order": 150,
    },
    {
        "name": "70-20-10 Model",
        "slug": "70-20-10-model",
        "description": "Workplace learning mix: 70% experience, 20% social, 10% formal.",
        "source": "Lombardo & Eichinger",
        "sort_order": 160,
    },
    {
        "name": "Balanced Scorecard (L&D)",
        "slug": "balanced-scorecard-ld",
        "description": "Strategy-aligned measures across financial, customer, internal, learning & growth.",
        "source": "Kaplan & Norton",
        "sort_order": 170,
    },
    {
        "name": "OKR Alignment",
        "slug": "okr-alignment",
        "description": "Objectives and Key Results methodology applied to L&D outcomes and impact.",
        "source": "Doerr / Google OKRs",
        "sort_order": 180,
    },
    {
        "name": "Capability Maturity (L&D)",
        "slug": "capability-maturity-ld",
        "description": "Maturity model for L&D capabilities and processes.",
        "source": "CMMI-inspired",
        "sort_order": 190,
    },
]

UPSERT_SQL = (
    """
    INSERT INTO frameworks (name, slug, description, source, is_builtin, is_active, sort_order, created_date)
    VALUES (:name, :slug, :description, :source, 1, 1, :sort_order, :created_date)
    ON CONFLICT(name) DO UPDATE SET
        slug=excluded.slug,
        description=excluded.description,
        source=excluded.source,
        is_builtin=1,
        is_active=1,
        sort_order=excluded.sort_order
    """
)

def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    inserted = 0
    for fw in FRAMEWORKS:
        payload = dict(fw)
        payload["created_date"] = NOW
        cur.execute(UPSERT_SQL, payload)
        if cur.rowcount == 1:
            # Could be insert or update; detect via querying by name
            cur.execute("SELECT id FROM frameworks WHERE name = ?", (fw["name"],))
            _ = cur.fetchone()
            inserted += 1
    con.commit()

    # Show summary
    total = cur.execute("SELECT COUNT(*) FROM frameworks").fetchone()[0]
    names = [r[0] for r in cur.execute("SELECT name FROM frameworks ORDER BY sort_order, name").fetchall()]
    print(f"Upserted {inserted} framework records. Total frameworks: {total}")
    print("Frameworks:")
    for n in names:
        print(" -", n)

    con.close()

if __name__ == "__main__":
    main()
