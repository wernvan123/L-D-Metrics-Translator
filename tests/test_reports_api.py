import json
import pytest

from app import db
from app.models import ReportTemplate, DynamicReport, ClientCompany, ClientEngagement


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


def _create_workspace(name_suffix='A'):
    company = ClientCompany(name=f'Client {name_suffix}', slug=f'client_{name_suffix.lower()}')
    db.session.add(company)
    db.session.commit()
    engagement = ClientEngagement(client_company_id=company.id, name=f'Engagement {name_suffix}')
    db.session.add(engagement)
    db.session.commit()
    return company, engagement


def _set_active_workspace(client, company_id: int | None, engagement_id: int | None, session_id: str = 'sess-1234567890'):
    with client.session_transaction() as sess:
        if company_id is None:
            sess.pop('active_client_id', None)
        else:
            sess['active_client_id'] = company_id
        if engagement_id is None:
            sess.pop('active_engagement_id', None)
        else:
            sess['active_engagement_id'] = engagement_id
        sess['session_id'] = session_id


def test_reports_list_empty(client):
    resp = client.get('/api/reports')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'reports' in data
    assert data['count'] == 0
    assert data['reports'] == []


def test_reports_list_and_get(client, app):
    with app.app_context():
        company, engagement = _create_workspace('A')
        t = _create_template()
        r = _create_report(t.id, title='QA Report A', status='completed')
        r.client_company_id = company.id
        r.client_engagement_id = engagement.id
        db.session.commit()
        rid = r.id  # capture before leaving context to avoid DetachedInstanceError
        cid = company.id
        eid = engagement.id
    _set_active_workspace(client, cid, eid)
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


def test_reports_list_requires_active_workspace(client, app):
    with app.app_context():
        company, engagement = _create_workspace('A')
        t = _create_template()
        r = _create_report(t.id, title='Workspace Report', status='completed')
        r.client_company_id = company.id
        r.client_engagement_id = engagement.id
        db.session.commit()
    resp = client.get('/api/reports')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['count'] == 0
    assert data['reports'] == []


def test_reports_list_filters_to_active_workspace(client, app):
    with app.app_context():
        company_a, engagement_a = _create_workspace('A')
        company_b, engagement_b = _create_workspace('B')
        t = _create_template()
        report_a = _create_report(t.id, title='Workspace A Report', status='completed')
        report_a.client_company_id = company_a.id
        report_a.client_engagement_id = engagement_a.id
        report_b = _create_report(t.id, title='Workspace B Report', status='completed')
        report_b.client_company_id = company_b.id
        report_b.client_engagement_id = engagement_b.id
        db.session.commit()
        rid_a = report_a.id
        company_a_id = company_a.id
        engagement_a_id = engagement_a.id
    _set_active_workspace(client, company_a_id, engagement_a_id)
    resp = client.get('/api/reports')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['count'] == 1
    assert [item['id'] for item in data['reports']] == [rid_a]


def test_reports_get_returns_404_for_workspace_mismatch(client, app):
    with app.app_context():
        company_a, engagement_a = _create_workspace('A')
        company_b, engagement_b = _create_workspace('B')
        t = _create_template()
        report_b = _create_report(t.id, title='Workspace B Report', status='completed')
        report_b.client_company_id = company_b.id
        report_b.client_engagement_id = engagement_b.id
        db.session.commit()
        rid_b = report_b.id
        company_a_id = company_a.id
        engagement_a_id = engagement_a.id
    _set_active_workspace(client, company_a_id, engagement_a_id)
    resp = client.get(f'/api/reports/{rid_b}')
    assert resp.status_code == 404


def test_reports_get_404(client):
    resp = client.get('/api/reports/999999')
    assert resp.status_code == 404
