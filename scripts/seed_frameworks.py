"""
Seed initial leadership frameworks and competencies.
Run: PYTHONPATH="<project>/ld-metrics-translator" python scripts/seed_frameworks.py
"""
from datetime import datetime, timezone
from typing import List

from app import create_app, db
from app.models import Framework, Competency


def slugify(name: str) -> str:
    import re
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s


def get_or_create_framework(name: str, description: str = None, source: str = None, sort_order: int = 0) -> Framework:
    slug = slugify(name)
    fw = Framework.query.filter_by(slug=slug).first()
    if fw:
        return fw
    fw = Framework(
        name=name,
        slug=slug,
        description=description,
        source=source,
        sort_order=sort_order,
        is_builtin=True,
        is_active=True,
        created_date=datetime.now(timezone.utc),
    )
    db.session.add(fw)
    db.session.commit()
    return fw


def ensure_competencies(fw: Framework, names: List[str]):
    existing = {c.slug: c for c in fw.competencies}
    order = 0
    for n in names:
        c_slug = slugify(n)
        if c_slug in existing:
            continue
        comp = Competency(
            framework_id=fw.id,
            name=n,
            slug=c_slug,
            sort_order=order,
        )
        db.session.add(comp)
        order += 1
    db.session.commit()


def main():
    app = create_app()
    with app.app_context():
        # Example: Goleman Emotional Intelligence
        fw = get_or_create_framework(
            name="Goleman Emotional Intelligence",
            description="Emotional intelligence competencies per Daniel Goleman's model.",
            source="Daniel Goleman",
            sort_order=10,
        )
        ensure_competencies(
            fw,
            [
                "Self-Awareness",
                "Self-Management",
                "Social Awareness",
                "Relationship Management",
            ],
        )

        # Example: Situational Leadership
        fw2 = get_or_create_framework(
            name="Situational Leadership",
            description="Leadership styles aligned to follower readiness.",
            source="Hersey-Blanchard",
            sort_order=20,
        )
        ensure_competencies(
            fw2,
            [
                "Directing",
                "Coaching",
                "Supporting",
                "Delegating",
            ],
        )

        print("Seeded frameworks:", [fw.slug, fw2.slug])


if __name__ == "__main__":
    main()
