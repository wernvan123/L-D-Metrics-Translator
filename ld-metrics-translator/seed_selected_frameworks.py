import sqlite3
from datetime import datetime

DB_PATH = r"app.db"

# Four frameworks provided by the user with their competencies
FRAMEWORKS = [
    {
        "name": "The Situational Leadership® Model",
        "slug": "situational-leadership-model",
        "description": "Leadership style adaptability across situations and follower readiness.",
        "source": "Hersey-Blanchard",
        "sort_order": 10,
        "competencies": [
            ("Adaptability", "adaptability", "Adjust leadership style to the needs of the situation", 10),
            ("Coaching", "coaching", "Guide, develop, and support team members to grow skills", 20),
            ("Delegation", "delegation", "Assign responsibility and authority effectively", 30),
            ("Motivation", "motivation", "Inspire and sustain individual and team motivation", 40),
        ],
    },
    {
        "name": "Goleman's Emotional Intelligence (EQ)",
        "slug": "goleman-emotional-intelligence-eq",
        "description": "Emotional intelligence domains and competencies per Daniel Goleman.",
        "source": "Daniel Goleman",
        "sort_order": 20,
        "competencies": [
            ("Self-Awareness", "self-awareness", "Recognize and understand own emotions", 10),
            ("Self-Management", "self-management", "Manage impulses and adapt to change", 20),
            ("Social Awareness", "social-awareness", "Empathy and organizational awareness", 30),
            ("Relationship Management", "relationship-management", "Influence, coach, and manage conflict", 40),
        ],
    },
    {
        "name": "The Five Practices of Exemplary Leadership",
        "slug": "five-practices-of-exemplary-leadership",
        "description": "Kouzes and Posner's model of five core leadership practices.",
        "source": "Kouzes & Posner",
        "sort_order": 30,
        "competencies": [
            ("Model the Way", "model-the-way", "Clarify values and set the example", 10),
            ("Inspire a Shared Vision", "inspire-a-shared-vision", "Envision the future and enlist others", 20),
            ("Challenge the Process", "challenge-the-process", "Search for opportunities and experiment", 30),
            ("Enable Others to Act", "enable-others-to-act", "Foster collaboration and strengthen others", 40),
            ("Encourage the Heart", "encourage-the-heart", "Recognize contributions and celebrate values and victories", 50),
        ],
    },
    {
        "name": "Strengths-Based Leadership",
        "slug": "strengths-based-leadership",
        "description": "Gallup's four domain model of leadership strengths.",
        "source": "Gallup",
        "sort_order": 40,
        "competencies": [
            ("Executing", "executing", "Make things happen and implement solutions", 10),
            ("Influencing", "influencing", "Take charge, speak up, and ensure ideas are heard", 20),
            ("Relationship Building", "relationship-building", "Build strong relationships that hold a team together", 30),
            ("Strategic Thinking", "strategic-thinking", "Absorb and analyze information to make better decisions", 40),
        ],
    },
]

UPSERT_FW = (
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


def get_fw_id(cur, name):
    row = cur.execute("SELECT id FROM frameworks WHERE name = ?", (name,)).fetchone()
    return row[0] if row else None


def upsert_competency(cur, framework_id, name, slug, description, sort_order):
    row = cur.execute(
        "SELECT id FROM competencies WHERE framework_id = ? AND name = ?",
        (framework_id, name),
    ).fetchone()
    if row:
        cur.execute(
            "UPDATE competencies SET slug = ?, description = ?, sort_order = ? WHERE id = ?",
            (slug, description, sort_order, row[0]),
        )
        return False
    else:
        cur.execute(
            "INSERT INTO competencies (framework_id, name, slug, description, sort_order) VALUES (?, ?, ?, ?, ?)",
            (framework_id, name, slug, description, sort_order),
        )
        return True


def get_fw_by_slug(cur, slug):
    row = cur.execute("SELECT id, name FROM frameworks WHERE slug = ?", (slug,)).fetchone()
    if not row:
        return None
    return { 'id': row[0], 'name': row[1] }


def ensure_unique_slug(cur, base_slug):
    """Return a slug that does not collide with existing frameworks.slug."""
    slug = base_slug
    suffix = 2
    while True:
        row = cur.execute("SELECT 1 FROM frameworks WHERE slug = ?", (slug,)).fetchone()
        if not row:
            return slug
        slug = f"{base_slug}-{suffix}"
        suffix += 1


def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    total_fw = 0
    total_comp_ins = 0
    total_comp_upd = 0

    for fw in FRAMEWORKS:
        fw_name = fw['name']
        desired_slug = fw['slug']
        description = fw.get('description')
        source = fw.get('source')
        sort_order = fw.get('sort_order', 0)

        # If a framework with this name exists, update it
        fw_id = get_fw_id(cur, fw_name)
        if fw_id:
            # If slug is taken by a different record, compute a unique variant
            slug_owner = get_fw_by_slug(cur, desired_slug)
            slug_to_use = desired_slug
            if slug_owner and slug_owner['id'] != fw_id:
                slug_to_use = ensure_unique_slug(cur, desired_slug)
            cur.execute(
                "UPDATE frameworks SET slug = ?, description = ?, source = ?, is_builtin = 1, is_active = 1, sort_order = ? WHERE id = ?",
                (slug_to_use, description, source, sort_order, fw_id),
            )
        else:
            # Ensure slug uniqueness before insert
            slug_to_use = ensure_unique_slug(cur, desired_slug)
            cur.execute(
                "INSERT INTO frameworks (name, slug, description, source, is_builtin, is_active, sort_order, created_date) VALUES (?, ?, ?, ?, 1, 1, ?, ?)",
                (fw_name, slug_to_use, description, source, sort_order, now),
            )
            fw_id = get_fw_id(cur, fw_name)
        total_fw += 1

        ins = upd = 0
        for c_name, c_slug, c_desc, c_order in fw.get('competencies', []):
            inserted = upsert_competency(cur, fw_id, c_name, c_slug, c_desc, c_order)
            if inserted:
                ins += 1
            else:
                upd += 1
        total_comp_ins += ins
        print(f"Framework '{fw_name}' -> competencies +{ins} / ~{upd}")

    con.commit()

    # Summary
    fw_count = cur.execute("SELECT COUNT(*) FROM frameworks").fetchone()[0]
    print(f"Upserted {total_fw} frameworks; DB frameworks total: {fw_count}")
    print(f"Competencies inserted {total_comp_ins}, updated {total_comp_upd}")

    con.close()


if __name__ == '__main__':
    main()
