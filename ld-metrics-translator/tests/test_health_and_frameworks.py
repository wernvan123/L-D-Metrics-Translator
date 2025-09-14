import json
import pytest

from app import db
from app.models import Framework


@pytest.mark.unit
@pytest.mark.api
class TestHealthAndFrameworks:
    """Minimal tests for health and frameworks endpoints."""

    def test_health_endpoint(self, client):
        resp = client.get('/api/health')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data is not None
        assert data.get('status') == 'healthy'
        # version marker to confirm correct health implementation is loaded
        assert data.get('api_version_marker') == 'fw-crud-v1'

    def test_frameworks_endpoint(self, client, app_context):
        # Ensure at least one framework exists
        if Framework.query.count() == 0:
            db.session.add(Framework(name='Test Framework', slug='test-framework', is_active=True, sort_order=1))
            db.session.commit()

        resp = client.get('/api/frameworks')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'frameworks' in data
        assert isinstance(data['frameworks'], list)
        assert 'total' in data
        assert data['total'] >= 1
        if data['frameworks']:
            fw = data['frameworks'][0]
            assert 'name' in fw and 'slug' in fw
