import os
import sys
import pytest
from sqlalchemy.pool import StaticPool

# Ensure the 'ld-metrics-translator' package is importable as 'app'
CURRENT_DIR = os.path.dirname(__file__)
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
PKG_DIR = os.path.join(REPO_ROOT, 'ld-metrics-translator')
if PKG_DIR not in sys.path:
    sys.path.insert(0, PKG_DIR)

# Prevent default app creation inside app/__init__.py during tests
os.environ['DISABLE_DEFAULT_FLASK_APP'] = '1'

from app import create_app, db
from app.models import AdminUser, LDOutcome, MetricType, Metric


@pytest.fixture(scope='function')
def app():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret',
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'connect_args': {'check_same_thread': False},
            'poolclass': StaticPool,
        },
    })

    with app.app_context():
        db.create_all()
        # Create admin user with API key for auth
        admin = AdminUser(username='admin', email='admin@example.com', is_active=True)
        admin.api_key = 'test-api-key'
        # Set a password if model requires hashing method
        try:
            admin.set_password('password')
        except Exception:
            pass
        db.session.add(admin)
        db.session.commit()

    yield app

    # Teardown
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_headers():
    return {'X-API-Key': 'test-api-key', 'Content-Type': 'application/json'}


@pytest.fixture()
def sample_metric_ids(app):
    """Create a couple of metrics and return their IDs for association tests."""
    with app.app_context():
        outcome = LDOutcome(name='Performance')
        mtype = MetricType(name='Quantitative')
        db.session.add_all([outcome, mtype])
        db.session.commit()

        m1 = Metric(name='Training Completion Rate', description='Rate', outcome_id=outcome.id, metric_type_id=mtype.id)
        m2 = Metric(name='Assessment Score', description='Score', outcome_id=outcome.id, metric_type_id=mtype.id)
        db.session.add_all([m1, m2])
        db.session.commit()
        return [m1.id, m2.id]
