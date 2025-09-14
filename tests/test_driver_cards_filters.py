import json
import pytest

from app import db
from app.models import Framework, Competency, LDOutcome, MetricType, Metric


def _mk_fw_comp_metric():
    # Create minimal data: outcome, type, 2 metrics, framework, competency, link 1 metric
    outcome = LDOutcome(name='Engagement')
    mtype = MetricType(name='Behavioral')
    db.session.add_all([outcome, mtype])
    db.session.commit()

    m1 = Metric(name='Onboarding Flow Optimization', description='Desc', outcome_id=outcome.id, metric_type_id=mtype.id)
    m2 = Metric(name='Unrelated Metric', description='Desc', outcome_id=outcome.id, metric_type_id=mtype.id)
    db.session.add_all([m1, m2])
    db.session.commit()

    fw = Framework(name='EIG', slug='eig')
    db.session.add(fw)
    db.session.commit()

    comp = Competency(name='Self-Awareness', slug='self-awareness', framework_id=fw.id)
    db.session.add(comp)
    db.session.commit()

    # Associate m1 with competency
    comp.metrics.append(m1)
    db.session.commit()

    return fw.id, comp.id, m1.id, m2.id


def test_driver_cards_filters_framework_and_competency(client, app):
    # Enable driver cards feature
    app.config['DRIVER_CARDS_V1'] = True
    with app.app_context():
        fw_id, comp_id, m1_id, m2_id = _mk_fw_comp_metric()

    # When filtering by both framework and competency, only m1 should appear
    res = client.get(f"/api/driver-cards?framework_id={fw_id}&competency_id={comp_id}&page_size=50")
    assert res.status_code == 200
    data = res.get_json()
    ids = [item['id'] for item in data.get('items', [])]
    assert m1_id in ids
    assert m2_id not in ids

    # Filtering by framework only should include m1 and exclude m2 (since m2 has no comp linkage)
    res2 = client.get(f"/api/driver-cards?framework_id={fw_id}&page_size=50")
    assert res2.status_code == 200
    data2 = res2.get_json()
    ids2 = [item['id'] for item in data2.get('items', [])]
    assert m1_id in ids2
    assert m2_id not in ids2
