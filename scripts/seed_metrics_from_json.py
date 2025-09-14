"""
Data-driven seeding of Metrics and deterministic linking to Competencies via JSON files.

Files:
- scripts/data/metrics.json  -> list of {name, description, outcome, type}
- scripts/data/competency_metric_map.json -> {"framework_slug:competency_slug": [metric_name, ...]}

Run:
  PYTHONPATH="<project>/ld-metrics-translator" python scripts/seed_metrics_from_json.py
"""
import json
from pathlib import Path
from typing import Dict, List, Tuple

from app import create_app, db
from app.models import LDOutcome, MetricType, Metric, Framework, Competency

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / 'data'
METRICS_FILE = DATA_DIR / 'metrics.json'
LINKS_FILE = DATA_DIR / 'competency_metric_map.json'


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


def upsert_metric(name: str, description: str, outcome_name: str, type_name: str) -> Metric:
    outcome = get_or_create_outcome(outcome_name)
    mtype = get_or_create_type(type_name)

    m = Metric.query.filter_by(name=name).first()
    if m:
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
        if dirty:
            db.session.add(m)
        return m

    m = Metric(
        name=name,
        description=description,
        outcome_id=outcome.id,
        metric_type_id=mtype.id,
    )
    db.session.add(m)
    db.session.flush()
    return m


def seed_metrics(metrics_data: List[dict]) -> Dict[str, Metric]:
    metrics_by_name: Dict[str, Metric] = {}
    for item in metrics_data:
        name = item.get('name')
        if not name:
            continue
        desc = item.get('description') or name
        outcome = item.get('outcome') or 'Engagement'
        mtype = item.get('type') or 'KPI'
        m = upsert_metric(name, desc, outcome, mtype)
        metrics_by_name[name] = m
    db.session.commit()
    print(f"Upserted {len(metrics_by_name)} metrics from JSON")
    return metrics_by_name


def link_from_map(link_map: Dict[str, List[str]], metrics_by_name: Dict[str, Metric]):
    total_links = 0
    for key, metric_names in link_map.items():
        try:
            fw_slug, comp_slug = key.split(':', 1)
        except ValueError:
            print(f"Skipping invalid key (expected 'framework:competency'): {key}")
            continue
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
    print(f"Total links added from map: {total_links}")


def main():
    app = create_app()
    with app.app_context():
        if not METRICS_FILE.exists() or not LINKS_FILE.exists():
            print(f"Missing data files in {DATA_DIR}")
            return
        metrics_data = json.loads(METRICS_FILE.read_text(encoding='utf-8'))
        link_map = json.loads(LINKS_FILE.read_text(encoding='utf-8'))

        metrics_by_name = seed_metrics(metrics_data)
        link_from_map(link_map, metrics_by_name)


if __name__ == '__main__':
    main()
