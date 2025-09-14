"""
Comprehensive tests for the Context Management System
Tests for ContextManager, database models, and API endpoints
"""

import pytest
import json
import uuid
from datetime import datetime, timedelta, timezone
from flask import Flask
from app import create_app, db
from app.models import Metric, LDOutcome, MetricType, UserSession, UserContext, MetricSelection
from app.context_manager import ContextManager
import tempfile
import os


@pytest.fixture
def app():
    """Create test Flask application."""
    # Create temporary database
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app('testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        
        # Create test data
        create_test_data()
        
        yield app
        
        db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def context_manager():
    """Create ContextManager instance for testing."""
    return ContextManager()


def create_test_data():
    """Create test data for context management tests."""
    # Create test L&D outcomes
    outcome1 = LDOutcome(name='Employee Engagement', description='Test outcome 1')
    outcome2 = LDOutcome(name='Performance Improvement', description='Test outcome 2')
    
    # Create test metric types
    type1 = MetricType(name='Operational KPI', description='Test type 1')
    type2 = MetricType(name='Behavioral Metric', description='Test type 2')
    
    db.session.add_all([outcome1, outcome2, type1, type2])
    db.session.commit()
    
    # Create test metrics
    metric1 = Metric(
        name='Employee Satisfaction Score',
        description='Measures employee satisfaction levels',
        outcome_id=outcome1.id,
        metric_type_id=type1.id
    )
    metric2 = Metric(
        name='Training Completion Rate',
        description='Percentage of employees completing training',
        outcome_id=outcome2.id,
        metric_type_id=type2.id
    )
    
    db.session.add_all([metric1, metric2])
    db.session.commit()


class TestUserSessionModel:
    """Test UserSession model functionality."""
    
    def test_create_user_session(self, app):
        """Test creating a user session."""
        with app.app_context():
            session_id = str(uuid.uuid4())
            session = UserSession(
                session_id=session_id,
                user_identifier='test_user',
                user_agent='Test Browser',
                ip_address='127.0.0.1'
            )
            
            db.session.add(session)
            db.session.commit()
            
            assert session.id is not None
            assert session.session_id == session_id
            assert session.is_active is True
            assert session.created_date is not None
    
    def test_get_or_create_session(self, app):
        """Test get_or_create class method."""
        with app.app_context():
            session_id = str(uuid.uuid4())
            
            # First call should create new session
            session1 = UserSession.get_or_create(session_id, 'test_user')
            assert session1.session_id == session_id
            
            # Second call should return existing session
            session2 = UserSession.get_or_create(session_id, 'test_user')
            assert session1.id == session2.id
    
    def test_update_activity(self, app):
        """Test updating session activity."""
        with app.app_context():
            session = UserSession.get_or_create(str(uuid.uuid4()), 'test_user')
            original_activity = session.last_activity
            
            # Wait a moment and update activity
            import time
            time.sleep(0.1)
            session.update_activity()
            
            assert session.last_activity > original_activity


class TestUserContextModel:
    """Test UserContext model functionality."""
    
    def test_create_user_context(self, app):
        """Test creating user context."""
        with app.app_context():
            session = UserSession.get_or_create(str(uuid.uuid4()), 'test_user')
            
            context_data = {'key': 'value', 'number': 42}
            context = UserContext(
                session_id=session.id,
                context_type='test',
                context_key='test_key',
                context_data=json.dumps(context_data)
            )
            
            db.session.add(context)
            db.session.commit()
            
            assert context.id is not None
            assert context.context_type == 'test'
            assert context.context_key == 'test_key'
            
            # Test to_dict method
            context_dict = context.to_dict()
            assert context_dict['context_data'] == context_data
    
    def test_context_validation(self, app):
        """Test context data validation."""
        with app.app_context():
            session = UserSession.get_or_create(str(uuid.uuid4()), 'test_user')
            
            # Test empty context type validation
            with pytest.raises(ValueError):
                context = UserContext(
                    session_id=session.id,
                    context_type='',
                    context_key='test_key',
                    context_data='{"test": "data"}'
                )
                db.session.add(context)
                db.session.commit()
    
    def test_context_expiration(self, app):
        """Test context expiration functionality."""
        with app.app_context():
            session = UserSession.get_or_create(str(uuid.uuid4()), 'test_user')
            
            # Create expired context
            context = UserContext(
                session_id=session.id,
                context_type='test',
                context_key='expired',
                context_data='{"test": "data"}',
                expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
            )
            
            db.session.add(context)
            db.session.commit()
            
            assert context.is_expired() is True


class TestMetricSelectionModel:
    """Test MetricSelection model functionality."""
    
    def test_create_metric_selection(self, app):
        """Test creating metric selection."""
        with app.app_context():
            session = UserSession.get_or_create(str(uuid.uuid4()), 'test_user')
            metric = Metric.query.first()
            
            selection = MetricSelection(
                session_id=session.id,
                metric_id=metric.id,
                selection_type='manual'
            )
            
            db.session.add(selection)
            db.session.commit()
            
            assert selection.id is not None
            assert selection.is_active is True
            assert selection.metric_id == metric.id
    
    def test_toggle_selection(self, app):
        """Test toggling metric selection."""
        with app.app_context():
            session = UserSession.get_or_create(str(uuid.uuid4()), 'test_user')
            metric = Metric.query.first()
            
            # First toggle should select
            selected, selection1 = MetricSelection.toggle_selection(
                session.id, metric.id, 'manual'
            )
            assert selected is True
            assert selection1.is_active is True
            
            # Second toggle should deselect
            selected, selection2 = MetricSelection.toggle_selection(
                session.id, metric.id, 'manual'
            )
            assert selected is False
            assert selection1.is_active is False  # Same object, updated
    
    def test_get_active_for_session(self, app):
        """Test getting active selections for session."""
        with app.app_context():
            session = UserSession.get_or_create(str(uuid.uuid4()), 'test_user')
            metrics = Metric.query.limit(2).all()
            
            # Select two metrics
            for metric in metrics:
                MetricSelection.toggle_selection(session.id, metric.id)
            
            active_selections = MetricSelection.get_active_for_session(session.id)
            assert len(active_selections) == 2


class TestContextManager:
    """Test ContextManager class functionality."""
    
    def test_context_manager_initialization(self, app, context_manager):
        """Test ContextManager initialization."""
        with app.app_context():
            assert context_manager.default_context_expiry == timedelta(hours=24)
            assert context_manager.session_timeout == timedelta(hours=2)
    
    def test_store_and_get_context(self, app, context_manager):
        """Test storing and retrieving context."""
        with app.test_request_context('/', headers={'User-Agent': 'Test'}):
            with app.app_context():
                test_data = {'test': 'value', 'number': 123}
                
                # Store context
                context = context_manager.store_context(
                    'test_type', 'test_key', test_data
                )
                assert context is not None
                
                # Retrieve context
                retrieved_data = context_manager.get_context('test_type', 'test_key')
                assert retrieved_data == test_data
    
    def test_store_search_context(self, app, context_manager):
        """Test storing search context."""
        with app.test_request_context('/', headers={'User-Agent': 'Test'}):
            with app.app_context():
                context = context_manager.store_search_context(
                    'engagement', {'outcome': 1}, 10
                )
                assert context is not None
                
                # Verify stored data
                retrieved = context_manager.get_context('search', 'last_search')
                assert retrieved['query'] == 'engagement'
                assert retrieved['results_count'] == 10
    
    def test_user_preferences(self, app, context_manager):
        """Test user preferences functionality."""
        with app.test_request_context('/', headers={'User-Agent': 'Test'}):
            with app.app_context():
                # Test default preferences
                prefs = context_manager.get_user_preferences()
                assert 'theme' in prefs
                assert prefs['theme'] == 'light'
                
                # Store custom preferences
                custom_prefs = {'theme': 'dark', 'results_per_page': 50}
                context_manager.store_user_preferences(custom_prefs)
                
                # Retrieve updated preferences
                updated_prefs = context_manager.get_user_preferences()
                assert updated_prefs['theme'] == 'dark'
                assert updated_prefs['results_per_page'] == 50
    
    def test_metric_selection(self, app, context_manager):
        """Test metric selection functionality."""
        with app.test_request_context('/', headers={'User-Agent': 'Test'}):
            with app.app_context():
                metric = Metric.query.first()
                
                # Select metric
                selected, selection = context_manager.select_metric(metric.id)
                assert selected is True
                assert selection.metric_id == metric.id
                
                # Check if metric is selected
                selected_metrics = context_manager.get_selected_metrics()
                assert len(selected_metrics) == 1
                assert selected_metrics[0]['metric_id'] == metric.id
                
                # Deselect metric
                selected, selection = context_manager.select_metric(metric.id)
                assert selected is False
    
    def test_clear_metric_selections(self, app, context_manager):
        """Test clearing all metric selections."""
        with app.test_request_context('/', headers={'User-Agent': 'Test'}):
            with app.app_context():
                metrics = Metric.query.limit(2).all()
                
                # Select multiple metrics
                for metric in metrics:
                    context_manager.select_metric(metric.id)
                
                # Verify selections
                selected_metrics = context_manager.get_selected_metrics()
                assert len(selected_metrics) == 2
                
                # Clear selections
                success = context_manager.clear_metric_selections()
                assert success is True
                
                # Verify cleared
                selected_metrics = context_manager.get_selected_metrics()
                assert len(selected_metrics) == 0
    
    def test_cleanup_expired_sessions(self, app, context_manager):
        """Test cleanup of expired sessions."""
        with app.app_context():
            # Create expired session
            old_session = UserSession(
                session_id=str(uuid.uuid4()),
                user_identifier='old_user',
                last_activity=datetime.now(timezone.utc) - timedelta(hours=3)
            )
            db.session.add(old_session)
            db.session.commit()
            
            # Run cleanup
            cleaned_count = context_manager.cleanup_expired_sessions()
            assert cleaned_count >= 1


class TestContextAPI:
    """Test Context Management API endpoints."""
    
    def test_get_session_info(self, client):
        """Test GET /api/context/session endpoint."""
        response = client.get('/api/context/session')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'session' in data
        assert 'stats' in data
    
    def test_store_context_endpoint(self, client):
        """Test POST /api/context/store endpoint."""
        test_data = {
            'context_type': 'test',
            'context_key': 'api_test',
            'context_data': {'test': 'value'},
            'expires_in_hours': 12
        }
        
        response = client.post(
            '/api/context/store',
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
    
    def test_get_context_endpoint(self, client):
        """Test GET /api/context/get/<type>/<key> endpoint."""
        # First store some context
        test_data = {
            'context_type': 'test',
            'context_key': 'api_get_test',
            'context_data': {'test': 'get_value'}
        }
        
        client.post(
            '/api/context/store',
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        # Then retrieve it
        response = client.get('/api/context/get/test/api_get_test')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['context_data']['test'] == 'get_value'
    
    def test_metric_selection_endpoint(self, client, app):
        """Test POST /api/context/metrics/select endpoint."""
        with app.app_context():
            metric = Metric.query.first()
            
            test_data = {
                'metric_id': metric.id,
                'selection_type': 'manual',
                'context_tags': ['test']
            }
            
            response = client.post(
                '/api/context/metrics/select',
                data=json.dumps(test_data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['selected'] is True
    
    def test_get_selected_metrics_endpoint(self, client, app):
        """Test GET /api/context/metrics/selected endpoint."""
        with app.app_context():
            metric = Metric.query.first()
            
            # First select a metric
            test_data = {'metric_id': metric.id}
            client.post(
                '/api/context/metrics/select',
                data=json.dumps(test_data),
                content_type='application/json'
            )
            
            # Then get selected metrics
            response = client.get('/api/context/metrics/selected')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['count'] >= 1
    
    def test_initialize_context_endpoint(self, client):
        """Test POST /api/context/initialize endpoint."""
        test_data = {
            'page': 'dashboard',
            'preferences': {'theme': 'dark'}
        }
        
        response = client.post(
            '/api/context/initialize',
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'session' in data
        assert 'preferences' in data
    
    def test_invalid_metric_selection(self, client):
        """Test selecting invalid metric ID."""
        test_data = {'metric_id': 99999}  # Non-existent metric
        
        response = client.post(
            '/api/context/metrics/select',
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data


class TestContextIntegration:
    """Integration tests for the complete context management system."""
    
    def test_full_user_workflow(self, client, app):
        """Test complete user workflow with context management."""
        with app.app_context():
            # 1. Initialize context
            init_response = client.post(
                '/api/context/initialize',
                data=json.dumps({'page': 'dashboard'}),
                content_type='application/json'
            )
            assert init_response.status_code == 200
            
            # 2. Store search context
            search_data = {
                'context_type': 'search',
                'context_key': 'workflow_search',
                'context_data': {'query': 'engagement metrics', 'filters': {}}
            }
            search_response = client.post(
                '/api/context/store',
                data=json.dumps(search_data),
                content_type='application/json'
            )
            assert search_response.status_code == 200
            
            # 3. Select metrics
            metric = Metric.query.first()
            select_response = client.post(
                '/api/context/metrics/select',
                data=json.dumps({'metric_id': metric.id}),
                content_type='application/json'
            )
            assert select_response.status_code == 200
            
            # 4. Get session info to verify everything is working
            session_response = client.get('/api/context/session')
            assert session_response.status_code == 200
            
            session_data = json.loads(session_response.data)
            assert session_data['success'] is True
            assert session_data['stats']['active_selections_count'] >= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
