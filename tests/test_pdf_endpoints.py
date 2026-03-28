import io
from unittest.mock import patch

from app import db
from app.models import ReportTemplate, DynamicReport, ClientCompany, ClientEngagement


class _StubPDFGenerator:
    def generate_metrics_report(self, selected_metrics, recommendations, user_selections):
        return io.BytesIO(b'%PDF-1.4\nmetrics report\n')

    def generate_quick_summary(self, metrics):
        return io.BytesIO(b'%PDF-1.4\nsummary report\n')

    def generate_comparison_report(self, a_report, b_report, summary_html, key_changes):
        return io.BytesIO(b'%PDF-1.4\ncomparison report\n')


def _create_template():
    template = ReportTemplate(name='PDF Template', description='For PDF tests', template_type='basic')
    db.session.add(template)
    db.session.commit()
    return template


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


def _create_report(template_id: int, company_id: int, engagement_id: int, pdf_path: str | None = None, title: str = 'Report PDF'):
    report = DynamicReport(
        title=title,
        template_id=template_id,
        session_id='test-session',
        client_company_id=company_id,
        client_engagement_id=engagement_id,
        generation_status='completed',
        generation_progress=100,
        pdf_path=pdf_path,
        download_count=0,
    )
    db.session.add(report)
    db.session.commit()
    return report


def test_generate_report_returns_pdf(client, sample_metric_ids):
    with patch('app.pdf_routes.PDFReportGenerator', return_value=_StubPDFGenerator()):
        resp = client.post(
            '/pdf/generate-report',
            json={
                'metric_ids': sample_metric_ids,
                'recommendations': {'next_step': 'Run pilot'},
                'user_selections': {'categories': [], 'outcomes': [], 'context': 'demo'},
                'report_type': 'comprehensive',
            },
        )
    assert resp.status_code == 200
    assert resp.mimetype == 'application/pdf'
    assert resp.data.startswith(b'%PDF-1.4')
    content_disposition = resp.headers.get('Content-Disposition', '')
    assert 'attachment;' in content_disposition
    assert 'LD_Metrics_Report_' in content_disposition


def test_generate_report_requires_metric_ids(client):
    resp = client.post('/pdf/generate-report', json={'metric_ids': []})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data['error'] == 'At least one metric must be selected'


def test_generate_comparison_returns_pdf(client):
    with patch('app.pdf_routes.PDFReportGenerator', return_value=_StubPDFGenerator()):
        resp = client.post(
            '/pdf/generate-comparison',
            json={
                'a_report': {'title': 'Baseline Report', 'date': '2026-03-01'},
                'b_report': {'title': 'Follow-up Report', 'date': '2026-03-07'},
                'summary_html': '<p>Improved readiness.</p>',
                'key_changes': [{'label': 'Strategic Acumen', 'change': 20}],
                'filename': 'comparison.pdf',
            },
        )
    assert resp.status_code == 200
    assert resp.mimetype == 'application/pdf'
    assert resp.data.startswith(b'%PDF-1.4')
    assert 'comparison.pdf' in resp.headers.get('Content-Disposition', '')


def test_download_dynamic_report_requires_matching_workspace(client, app, tmp_path):
    with app.app_context():
        company_a, engagement_a = _create_workspace('A')
        company_b, engagement_b = _create_workspace('B')
        template = _create_template()
        pdf_path = tmp_path / 'report.pdf'
        pdf_path.write_bytes(b'%PDF-1.4\nworkspace report\n')
        report = _create_report(template.id, company_b.id, engagement_b.id, pdf_path=str(pdf_path), title='Workspace Locked')
        report_id = report.id
        company_a_id = company_a.id
        engagement_a_id = engagement_a.id
    _set_active_workspace(client, company_a_id, engagement_a_id)
    resp = client.get(f'/api/dynamic-reports/{report_id}/download')
    assert resp.status_code == 404


def test_download_dynamic_report_returns_pdf_and_increments_count(client, app, tmp_path):
    with app.app_context():
        company, engagement = _create_workspace('A')
        template = _create_template()
        pdf_path = tmp_path / 'report.pdf'
        pdf_path.write_bytes(b'%PDF-1.4\ndownloadable report\n')
        report = _create_report(template.id, company.id, engagement.id, pdf_path=str(pdf_path), title='Download Me')
        report_id = report.id
        company_id = company.id
        engagement_id = engagement.id
    _set_active_workspace(client, company_id, engagement_id)
    resp = client.get(f'/api/dynamic-reports/{report_id}/download')
    assert resp.status_code == 200
    assert resp.mimetype == 'application/pdf'
    assert resp.data.startswith(b'%PDF-1.4')
    content_disposition = resp.headers.get('Content-Disposition', '')
    assert 'attachment;' in content_disposition
    assert 'Download_Me.pdf' in content_disposition
    with app.app_context():
        updated = db.session.get(DynamicReport, report_id)
        assert updated.download_count == 1


def test_download_dynamic_report_returns_404_when_file_missing(client, app):
    with app.app_context():
        company, engagement = _create_workspace('A')
        template = _create_template()
        report = _create_report(
            template.id,
            company.id,
            engagement.id,
            pdf_path='C:/definitely/missing/report.pdf',
            title='Missing PDF',
        )
        report_id = report.id
        company_id = company.id
        engagement_id = engagement.id
    _set_active_workspace(client, company_id, engagement_id)
    resp = client.get(f'/api/dynamic-reports/{report_id}/download')
    assert resp.status_code == 404
    data = resp.get_json()
    assert data['error'] == 'PDF file not found'
