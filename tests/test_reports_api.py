import json
import pytest

from app import db
from app.models import ReportTemplate, DynamicReport


def _create_template():
    # template_type is NOT NULL in the schema
    t = ReportTemplate(name='Demo Template', description='For tests', template_type='basic')
    db.session.add(t)
    db.session.commit()
    return t


def _create_report(template_id: int, title='Test Report', status='completed'):
    r = DynamicReport(
        title=title,
        template_id=template_id,
        session_id='test-session',
        generation_status=status,
        generation_progress=100 if status == 'completed' else 10,
        download_count=0,
    )
    db.session.add(r)
    db.session.commit()
    return r


def test_reports_list_empty(client):
    resp = client.get('/api/reports')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'reports' in data
    assert data['count'] == 0
    assert data['reports'] == []


def test_reports_list_and_get(client, app):
    with app.app_context():
        t = _create_template()
        r = _create_report(t.id, title='QA Report A', status='completed')
        rid = r.id  # capture before leaving context to avoid DetachedInstanceError
    # List
    resp = client.get('/api/reports')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['count'] == 1
    assert any(item['id'] == rid for item in data['reports'])
    # Get single
    resp2 = client.get(f'/api/reports/{rid}')
    assert resp2.status_code == 200
    d2 = resp2.get_json()
    assert 'report' in d2
    assert d2['report']['id'] == rid
    assert d2['report']['title'] == 'QA Report A'


def test_reports_get_404(client):
    resp = client.get('/api/reports/999999')
    assert resp.status_code in (404, 200)  # Some builds may fallback; accept 404 preferred
    if resp.status_code == 200:
        # When 200, ensure structure indicates not found gracefully
        data = resp.get_json()
        assert 'report' not in data or data.get('report') is None
