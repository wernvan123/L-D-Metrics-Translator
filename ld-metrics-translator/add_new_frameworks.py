"""
Add new leadership frameworks to the database.
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
        # Add Five Practices of Exemplary Leadership
        fw1 = get_or_create_framework(
            name="Five Practices of Exemplary Leadership",
            description="Leadership framework based on Kouzes and Posner's research on exemplary leadership practices.",
            source="Kouzes & Posner",
            sort_order=30,
        )
        ensure_competencies(
            fw1,
            [
                "Model the Way",
                "Inspire a Shared Vision", 
                "Challenge the Process",
                "Enable Others to Act",
                "Encourage the Heart",
            ],
        )

        # Add Strengths-Based Leadership
        fw2 = get_or_create_framework(
            name="Strengths-Based Leadership",
            description="Leadership approach focused on identifying and leveraging individual and team strengths.",
            source="Gallup StrengthsFinder",
            sort_order=40,
        )
        ensure_competencies(
            fw2,
            [
                "Executing",
                "Influencing", 
                "Relationship Building",
                "Strategic Thinking",
            ],
        )

        print("Successfully added new frameworks:")
        print(f"- {fw1.name} ({fw1.slug})")
        print(f"- {fw2.name} ({fw2.slug})")


if __name__ == "__main__":
    main()
