"""
Pytest configuration and fixtures for L&D Metrics Translator tests.
"""
import os
import tempfile
import pytest
from unittest.mock import patch

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    SELENIUM_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    webdriver = None
    Options = None
    SELENIUM_AVAILABLE = False

# Add project root to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import LDOutcome, MetricType, Metric, AdminUser
from app.database import init_database, seed_basic_data


@pytest.fixture(scope='session')
def app():
    """Create application for testing."""
    # Create a temporary file for the test database
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key'
    })
    
    with app.app_context():
        init_database()
        seed_basic_data()
        
    yield app
    
    # Clean up
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create test CLI runner."""
    return app.test_cli_runner()


@pytest.fixture
def app_context(app):
    """Create application context."""
    with app.app_context():
        # Ensure a clean database for each test
        db.drop_all()
        db.create_all()
        yield app


@pytest.fixture
def db_session(app_context):
    """Create database session for testing."""
    db.create_all()
    yield db.session
    db.session.rollback()
    db.drop_all()


@pytest.fixture
def sample_outcome():
    """Create a sample L&D outcome for testing."""
    outcome = LDOutcome(
        name="Test Outcome",
        description="A test learning outcome",
        category="Knowledge",
        level="Basic"
    )
    db.session.add(outcome)
    db.session.commit()
    return outcome


@pytest.fixture
def sample_metric_type():
    """Create a sample metric type for testing."""
    metric_type = MetricType(
        name="Test Metric Type",
        description="A test metric type",
        category="Assessment"
    )
    db.session.add(metric_type)
    db.session.commit()
    return metric_type


@pytest.fixture
def sample_metric(sample_outcome, sample_metric_type):
    """Create a sample metric for testing."""
    metric = Metric(
        name="Test Metric",
        description="A test metric",
        outcome_id=sample_outcome.id,
        metric_type_id=sample_metric_type.id,
        measurement_method="Survey",
        data_collection="Monthly",
        success_criteria="80% completion rate"
    )
    db.session.add(metric)
    db.session.commit()
    return metric


@pytest.fixture
def admin_user(app_context):
    """Create an admin user for testing."""
    user = AdminUser(
        username="testadmin",
        email="admin@test.com"
    )
    user.set_password("testpassword")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def regular_user(app_context):
    """Create a regular user for testing (non-admin)."""
    user = AdminUser(
        username="testuser",
        email="user@test.com"
    )
    user.set_password("testpassword")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture(scope="session")
def chrome_driver():
    """Create Chrome WebDriver for Selenium tests."""
    if not SELENIUM_AVAILABLE:
        pytest.skip("Selenium not installed; skipping browser-based tests")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    try:
        driver = webdriver.Chrome(options=options)
    except Exception as exc:  # pragma: no cover - environment specific
        pytest.skip(f"Chrome WebDriver unavailable: {exc}")

    yield driver
    driver.quit()


@pytest.fixture
def mock_email():
    """Mock email sending for tests."""
    with patch('app.admin.send_email') as mock:
        yield mock


@pytest.fixture
def performance_monitor():
    """Monitor performance metrics during tests."""
    try:
        import psutil
    except ImportError:  # pragma: no cover - optional dependency
        pytest.skip("psutil not installed; skipping performance monitoring")
    import time
    
    process = psutil.Process()
    start_time = time.time()
    start_memory = process.memory_info().rss
    
    yield
    
    end_time = time.time()
    end_memory = process.memory_info().rss
    
    execution_time = end_time - start_time
    memory_diff = end_memory - start_memory
    
    # Store metrics for reporting
    if not hasattr(pytest, 'performance_data'):
        pytest.performance_data = []
    
    pytest.performance_data.append({
        'execution_time': execution_time,
        'memory_usage': memory_diff
    })


# Test data factories
class OutcomeFactory:
    """Factory for creating test outcomes."""
    
    @staticmethod
    def create(**kwargs):
        defaults = {
            'name': 'Test Outcome',
            'description': 'Test description',
            'category': 'Knowledge',
            'level': 'Basic'
        }
        defaults.update(kwargs)
        outcome = LDOutcome(**defaults)
        db.session.add(outcome)
        db.session.commit()
        return outcome


class MetricTypeFactory:
    """Factory for creating test metric types."""
    
    @staticmethod
    def create(**kwargs):
        defaults = {
            'name': 'Test Metric Type',
            'description': 'Test description',
            'category': 'Assessment'
        }
        defaults.update(kwargs)
        metric_type = MetricType(**defaults)
        db.session.add(metric_type)
        db.session.commit()
        return metric_type


class MetricFactory:
    """Factory for creating test metrics."""
    
    @staticmethod
    def create(outcome=None, metric_type=None, **kwargs):
        if not outcome:
            outcome = OutcomeFactory.create()
        if not metric_type:
            metric_type = MetricTypeFactory.create()
            
        defaults = {
            'name': 'Test Metric',
            'description': 'Test description',
            'outcome_id': outcome.id,
            'metric_type_id': metric_type.id,
            'measurement_method': 'Survey',
            'data_collection': 'Monthly',
            'success_criteria': '80% completion'
        }
        defaults.update(kwargs)
        metric = Metric(**defaults)
        db.session.add(metric)
        db.session.commit()
        return metric
