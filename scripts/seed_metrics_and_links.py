"""
DEPRECATED: Use scripts/seed_metrics_from_json.py instead.
This script is kept for reference and may be removed in a future release.

Seed a small set of canonical Metrics and deterministically link them to competencies by slug.

Run:
  PYTHONPATH="<project>/ld-metrics-translator" python scripts/seed_metrics_and_links.py
"""
from typing import Dict, List, Tuple

from app import create_app, db
from app.models import LDOutcome, MetricType, Metric, Framework, Competency


def get_or_create_outcome(name: str, description: str = None) -> LDOutcome:
    o = LDOutcome.query.filter_by(name=name).first()
    if o:
        return o
    o = LDOutcome(name=name, description=description or name)
    db.session.add(o)
    db.session.commit()
    return o


def get_or_create_type(name: str, description: str = None) -> MetricType:
    t = MetricType.query.filter_by(name=name).first()
    if t:
        return t
    t = MetricType(name=name, description=description or name)
    db.session.add(t)
    db.session.commit()
    return t


def upsert_metric(name: str, description: str, outcome: LDOutcome, mtype: MetricType, **extra) -> Metric:
    m = Metric.query.filter_by(name=name).first()
    if m:
        # update core fields if changed
        dirty = False
        if m.description != description:
            m.description = description
            dirty = True
        if m.outcome_id != outcome.id:
            m.outcome_id = outcome.id
            dirty = True
        if m.metric_type_id != mtype.id:
            m.metric_type_id = mtype.id
            dirty = True
        for k, v in extra.items():
            if hasattr(m, k) and getattr(m, k) != v:
                setattr(m, k, v)
                dirty = True
        if dirty:
            db.session.add(m)
        return m
    m = Metric(
        name=name,
        description=description,
        outcome_id=outcome.id,
        metric_type_id=mtype.id,
        **{k: v for k, v in extra.items() if hasattr(Metric, k)},
    )
    db.session.add(m)
    db.session.flush()  # get id without full commit
    return m


def link_metrics(links: Dict[Tuple[str, str], List[str]], metrics_by_name: Dict[str, Metric]):
    total_links = 0
    for (fw_slug, comp_slug), metric_names in links.items():
        fw = Framework.query.filter_by(slug=fw_slug).first()
        if not fw:
            print(f"Framework not found: {fw_slug}")
            continue
        comp = Competency.query.filter_by(framework_id=fw.id, slug=comp_slug).first()
        if not comp:
            print(f"Competency not found: {fw_slug}:{comp_slug}")
            continue
        added_here = 0
        for name in metric_names:
            m = metrics_by_name.get(name)
            if not m:
                print(f"  Metric not found for linking: '{name}'")
                continue
            if m not in comp.metrics:
                comp.metrics.append(m)
                added_here += 1
        if added_here:
            db.session.add(comp)
            total_links += added_here
            print(f"Linked {added_here} metrics to {fw_slug}:{comp_slug} (now {len(comp.metrics)} total)")
    if total_links:
        db.session.commit()
    print(f"Total links added: {total_links}")


def main():
    app = create_app()
    with app.app_context():
        print("WARNING: seed_metrics_and_links.py is deprecated. Use scripts/seed_metrics_from_json.py with scripts/data/*.json.")
        # Ensure baseline taxonomy exists
        engagement = get_or_create_outcome("Engagement")
        productivity = get_or_create_outcome("Productivity")
        retention = get_or_create_outcome("Retention")

        kpi = get_or_create_type("KPI")
        behavioral = get_or_create_type("Behavioral")
        assessment = get_or_create_type("Assessment")

        # Canonical metrics to seed (names used as natural keys)
        seeds = [
            ("360 Feedback Score", "Average score from 360-degree feedback assessments.", engagement, assessment),
            ("Self-Assessment Completion Rate", "Percentage of participants completing self-assessments.", engagement, behavioral),
            ("Pulse Survey eNPS", "Employee Net Promoter Score from pulse surveys.", engagement, kpi),
            ("On-Time Delivery Rate", "Percent of deliverables completed by the agreed deadline.", productivity, kpi),
            ("Absenteeism Rate", "Average days absent per employee per period.", productivity, kpi),
            ("Collaboration Index", "Composite score reflecting cross-functional collaboration.", engagement, behavioral),
            ("Manager Feedback Quality", "Qualitative rating of feedback quality from managers.", engagement, assessment),
            ("Time to Productivity", "Time for new hires to reach target productivity.", productivity, kpi),
            ("Error Rate", "Number of errors per 1,000 transactions.", productivity, kpi),
            ("Learning Retention Score", "Post-training knowledge retention assessment score.", retention, assessment),
        ]

        metrics_by_name: Dict[str, Metric] = {}
        for name, desc, outcome, mtype in seeds:
            m = upsert_metric(name, desc, outcome, mtype)
            metrics_by_name[name] = m
        db.session.commit()
        print(f"Seeded {len(metrics_by_name)} metrics (upserted)")

        # Deterministic links by framework:competency -> metric names
        links = {
            ("goleman-emotional-intelligence", "self-awareness"): [
                "360 Feedback Score",
                "Self-Assessment Completion Rate",
            ],
            ("goleman-emotional-intelligence", "social-awareness"): [
                "Pulse Survey eNPS",
                "Manager Feedback Quality",
            ],
            ("goleman-emotional-intelligence", "self-management"): [
                "On-Time Delivery Rate",
                "Absenteeism Rate",
            ],
            ("goleman-emotional-intelligence", "relationship-management"): [
                "Collaboration Index",
                "Manager Feedback Quality",
            ],
            ("situational-leadership", "directing"): [
                "Time to Productivity",
                "Error Rate",
            ],
            ("situational-leadership", "coaching"): [
                "Learning Retention Score",
                "360 Feedback Score",
            ],
            ("situational-leadership", "supporting"): [
                "Collaboration Index",
                "Pulse Survey eNPS",
            ],
            ("situational-leadership", "delegating"): [
                "On-Time Delivery Rate",
                "Absenteeism Rate",
            ],
        }

        link_metrics(links, metrics_by_name)


if __name__ == "__main__":
    main()
