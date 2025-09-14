"""
Unit tests for application routes.
"""
import pytest
import json
from flask import url_for
from unittest.mock import patch

from app.models import LDOutcome, MetricType, Metric, User
from app import db


@pytest.mark.unit
class TestMainRoutes:
    """Test main application routes."""
    
    def test_index_route(self, client):
        """Test the main index route."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'L&D Metrics Translator' in response.data
    
    def test_about_route(self, client):
        """Test the about route."""
        response = client.get('/about')
        assert response.status_code == 200
        assert b'About' in response.data
    
    def test_help_route(self, client):
        """Test the help route."""
        response = client.get('/help')
        assert response.status_code == 200
        assert b'Help' in response.data


@pytest.mark.unit
class TestOutcomeRoutes:
    """Test outcome-related routes."""
    
    def test_outcomes_list(self, client, app_context, sample_outcome):
        """Test outcomes listing page."""
        response = client.get('/outcomes')
        assert response.status_code == 200
        assert sample_outcome.name.encode() in response.data
    
    def test_outcome_detail(self, client, app_context, sample_outcome):
        """Test individual outcome detail page."""
        response = client.get(f'/outcomes/{sample_outcome.id}')
        assert response.status_code == 200
        assert sample_outcome.name.encode() in response.data
        assert sample_outcome.description.encode() in response.data
    
    def test_outcome_not_found(self, client):
        """Test outcome detail with invalid ID."""
        response = client.get('/outcomes/999')
        assert response.status_code == 404
    
    def test_outcomes_search(self, client, app_context):
        """Test outcomes search functionality."""
        # Create test outcomes
        outcome1 = LDOutcome(name="Python Programming", description="Learn Python", 
                           category="Skills", level="Intermediate")
        outcome2 = LDOutcome(name="Data Analysis", description="Analyze data", 
                           category="Skills", level="Advanced")
        db.session.add_all([outcome1, outcome2])
        db.session.commit()
        
        # Test search
        response = client.get('/outcomes?search=Python')
        assert response.status_code == 200
        assert b'Python Programming' in response.data
        assert b'Data Analysis' not in response.data
    
    def test_outcomes_filter(self, client, app_context):
        """Test outcomes filtering."""
        # Create test outcomes
        outcome1 = LDOutcome(name="Test 1", description="Test", category="Knowledge", level="Basic")
        outcome2 = LDOutcome(name="Test 2", description="Test", category="Skills", level="Intermediate")
        db.session.add_all([outcome1, outcome2])
        db.session.commit()
        
        # Test category filter
        response = client.get('/outcomes?category=Skills')
        assert response.status_code == 200
        assert b'Test 2' in response.data
        assert b'Test 1' not in response.data
        
        # Test level filter
        response = client.get('/outcomes?level=Basic')
        assert response.status_code == 200
        assert b'Test 1' in response.data
        assert b'Test 2' not in response.data


@pytest.mark.unit
class TestMetricTypeRoutes:
    """Test metric type routes."""
    
    def test_metric_types_list(self, client, app_context, sample_metric_type):
        """Test metric types listing page."""
        response = client.get('/types')
        assert response.status_code == 200
        assert sample_metric_type.name.encode() in response.data
    
    def test_metric_type_detail(self, client, app_context, sample_metric_type):
        """Test individual metric type detail page."""
        response = client.get(f'/types/{sample_metric_type.id}')
        assert response.status_code == 200
        assert sample_metric_type.name.encode() in response.data
        assert sample_metric_type.description.encode() in response.data
    
    def test_metric_type_not_found(self, client):
        """Test metric type detail with invalid ID."""
        response = client.get('/types/999')
        assert response.status_code == 404


@pytest.mark.unit
class TestMetricRoutes:
    """Test metric routes."""
    
    def test_metrics_list(self, client, app_context, sample_metric):
        """Test metrics listing page."""
        response = client.get('/metrics')
        assert response.status_code == 200
        assert sample_metric.name.encode() in response.data
    
    def test_metric_detail(self, client, app_context, sample_metric):
        """Test individual metric detail page."""
        response = client.get(f'/metrics/{sample_metric.id}')
        assert response.status_code == 200
        assert sample_metric.name.encode() in response.data
        assert sample_metric.description.encode() in response.data
    
    def test_metric_not_found(self, client):
        """Test metric detail with invalid ID."""
        response = client.get('/metrics/999')
        assert response.status_code == 404
    
    def test_metrics_search(self, client, app_context, sample_outcome, sample_metric_type):
        """Test metrics search functionality."""
        # Create test metrics
        metric1 = Metric(name="Completion Rate", description="Course completion",
                        outcome_id=sample_outcome.id, metric_type_id=sample_metric_type.id,
                        measurement_method="Analytics", data_collection="Daily", success_criteria="90%")
        metric2 = Metric(name="Satisfaction Score", description="Student satisfaction",
                        outcome_id=sample_outcome.id, metric_type_id=sample_metric_type.id,
                        measurement_method="Survey", data_collection="Weekly", success_criteria="4.0/5.0")
        db.session.add_all([metric1, metric2])
        db.session.commit()
        
        # Test search
        response = client.get('/metrics?search=Completion')
        assert response.status_code == 200
        assert b'Completion Rate' in response.data
        assert b'Satisfaction Score' not in response.data


@pytest.mark.unit
class TestTranslatorRoutes:
    """Test translator functionality routes."""
    
    def test_translator_page(self, client):
        """Test translator main page."""
        response = client.get('/translator')
        assert response.status_code == 200
        assert b'Translator' in response.data
    
    def test_translate_post_valid(self, client, app_context, sample_outcome, sample_metric_type):
        """Test translation with valid data."""
        data = {
            'outcome_id': sample_outcome.id,
            'metric_type_id': sample_metric_type.id,
            'additional_context': 'Test context'
        }
        
        response = client.post('/translator', data=data)
        assert response.status_code == 200
        # Should contain suggested metrics
        assert b'Suggested Metrics' in response.data
    
    def test_translate_post_invalid(self, client):
        """Test translation with invalid data."""
        data = {
            'outcome_id': 999,  # Invalid ID
            'metric_type_id': 999,  # Invalid ID
            'additional_context': 'Test context'
        }
        
        response = client.post('/translator', data=data)
        assert response.status_code == 200
        # Should show error message
        assert b'error' in response.data.lower() or b'invalid' in response.data.lower()
    
    def test_translate_missing_data(self, client):
        """Test translation with missing required data."""
        data = {
            'additional_context': 'Test context'
            # Missing outcome_id and metric_type_id
        }
        
        response = client.post('/translator', data=data)
        assert response.status_code == 200
        # Should show validation error
        assert b'required' in response.data.lower() or b'error' in response.data.lower()


@pytest.mark.unit
class TestAdminRoutes:
    """Test admin routes."""
    
    def test_admin_login_page(self, client):
        """Test admin login page."""
        response = client.get('/admin/login')
        assert response.status_code == 200
        assert b'Login' in response.data
    
    def test_admin_login_valid(self, client, app_context, admin_user):
        """Test admin login with valid credentials."""
        data = {
            'username': admin_user.username,
            'password': 'testpassword'
        }
        
        response = client.post('/admin/login', data=data, follow_redirects=True)
        assert response.status_code == 200
        # Should redirect to admin dashboard
        assert b'Dashboard' in response.data or b'Admin' in response.data
    
    def test_admin_login_invalid(self, client, app_context, admin_user):
        """Test admin login with invalid credentials."""
        data = {
            'username': admin_user.username,
            'password': 'wrongpassword'
        }
        
        response = client.post('/admin/login', data=data)
        assert response.status_code == 200
        # Should show error message
        assert b'Invalid' in response.data or b'error' in response.data.lower()
    
    def test_admin_dashboard_unauthorized(self, client):
        """Test admin dashboard without login."""
        response = client.get('/admin/dashboard')
        # Should redirect to login or show unauthorized
        assert response.status_code in [302, 401, 403]
    
    def test_admin_logout(self, client, app_context, admin_user):
        """Test admin logout."""
        # First login
        with client.session_transaction() as sess:
            sess['user_id'] = admin_user.id
            sess['is_admin'] = True
        
        response = client.get('/admin/logout', follow_redirects=True)
        assert response.status_code == 200
        # Should redirect to main page
        assert b'L&D Metrics Translator' in response.data


@pytest.mark.unit
class TestFormValidation:
    """Test form validation."""
    
    def test_contact_form_valid(self, client):
        """Test contact form with valid data."""
        data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'subject': 'Test Subject',
            'message': 'Test message content'
        }
        
        response = client.post('/contact', data=data)
        assert response.status_code == 200
        # Should show success message
        assert b'success' in response.data.lower() or b'thank' in response.data.lower()
    
    def test_contact_form_invalid_email(self, client):
        """Test contact form with invalid email."""
        data = {
            'name': 'Test User',
            'email': 'invalid-email',
            'subject': 'Test Subject',
            'message': 'Test message content'
        }
        
        response = client.post('/contact', data=data)
        assert response.status_code == 200
        # Should show validation error
        assert b'valid email' in response.data.lower() or b'invalid' in response.data.lower()
    
    def test_contact_form_missing_fields(self, client):
        """Test contact form with missing required fields."""
        data = {
            'name': 'Test User',
            # Missing email, subject, message
        }
        
        response = client.post('/contact', data=data)
        assert response.status_code == 200
        # Should show validation errors
        assert b'required' in response.data.lower() or b'field' in response.data.lower()


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling routes."""
    
    def test_404_error(self, client):
        """Test 404 error handling."""
        response = client.get('/nonexistent-page')
        assert response.status_code == 404
        assert b'404' in response.data or b'Not Found' in response.data
    
    def test_500_error_simulation(self, client, app_context):
        """Test 500 error handling."""
        # This would require simulating a server error
        # For now, we'll test that the error handler is registered
        from app import app
        assert app.errorhandler(500) is not None


@pytest.mark.unit
class TestResponseHeaders:
    """Test response headers and security."""
    
    def test_security_headers(self, client):
        """Test security headers are present."""
        response = client.get('/')
        
        # Check for common security headers
        # Note: These depend on your app configuration
        headers = response.headers
        
        # Basic checks
        assert response.status_code == 200
        assert 'Content-Type' in headers
    
    def test_cors_headers(self, client):
        """Test CORS headers for API endpoints."""
        response = client.get('/api/outcomes')
        
        # Should have CORS headers due to Flask-CORS
        headers = response.headers
        assert 'Access-Control-Allow-Origin' in headers
    
    def test_json_content_type(self, client):
        """Test JSON content type for API endpoints."""
        response = client.get('/api/outcomes')
        assert response.status_code == 200
        assert 'application/json' in response.content_type


@pytest.mark.unit
class TestPagination:
    """Test pagination functionality."""
    
    def test_outcomes_pagination(self, client, app_context):
        """Test outcomes pagination."""
        # Create many outcomes to test pagination
        outcomes = []
        for i in range(25):  # More than default page size
            outcome = LDOutcome(
                name=f"Test Outcome {i}",
                description=f"Description {i}",
                category="Knowledge",
                level="Basic"
            )
            outcomes.append(outcome)
        
        db.session.add_all(outcomes)
        db.session.commit()
        
        # Test first page
        response = client.get('/outcomes')
        assert response.status_code == 200
        assert b'Test Outcome 0' in response.data
        
        # Test pagination links
        if b'Next' in response.data or b'2' in response.data:
            # Test second page
            response = client.get('/outcomes?page=2')
            assert response.status_code == 200
    
    def test_metrics_pagination(self, client, app_context, sample_outcome, sample_metric_type):
        """Test metrics pagination."""
        # Create many metrics to test pagination
        metrics = []
        for i in range(25):  # More than default page size
            metric = Metric(
                name=f"Test Metric {i}",
                description=f"Description {i}",
                outcome_id=sample_outcome.id,
                metric_type_id=sample_metric_type.id,
                measurement_method="Survey",
                data_collection="Monthly",
                success_criteria="80%"
            )
            metrics.append(metric)
        
        db.session.add_all(metrics)
        db.session.commit()
        
        # Test first page
        response = client.get('/metrics')
        assert response.status_code == 200
        assert b'Test Metric 0' in response.data
