"""
Unit tests for API endpoints.
"""
import pytest
import json
from unittest.mock import patch

from app.models import LDOutcome, MetricType, Metric
from app import db


@pytest.mark.unit
@pytest.mark.api
class TestOutcomesAPI:
    """Test outcomes API endpoints."""
    
    def test_get_outcomes_empty(self, client, app_context):
        """Test GET /api/outcomes with no data."""
        response = client.get('/api/outcomes')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'outcomes' in data
        assert isinstance(data['outcomes'], list)
        assert len(data['outcomes']) == 0
    
    def test_get_outcomes_with_data(self, client, app_context, sample_outcome):
        """Test GET /api/outcomes with data."""
        response = client.get('/api/outcomes')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'outcomes' in data
        assert len(data['outcomes']) == 1
        
        outcome_data = data['outcomes'][0]
        assert outcome_data['id'] == sample_outcome.id
        assert outcome_data['name'] == sample_outcome.name
        assert outcome_data['description'] == sample_outcome.description
        assert outcome_data['category'] == sample_outcome.category
        assert outcome_data['level'] == sample_outcome.level
    
    def test_get_outcomes_search(self, client, app_context):
        """Test GET /api/outcomes with search parameter."""
        # Create test outcomes
        outcome1 = LDOutcome(name="Python Programming", description="Learn Python", 
                           category="Skills", level="Intermediate")
        outcome2 = LDOutcome(name="Data Analysis", description="Analyze data with Python", 
                           category="Skills", level="Advanced")
        outcome3 = LDOutcome(name="Team Leadership", description="Lead teams effectively", 
                           category="Behavior", level="Advanced")
        
        db.session.add_all([outcome1, outcome2, outcome3])
        db.session.commit()
        
        # Test search by name
        response = client.get('/api/outcomes?search=Python')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert len(data['outcomes']) == 2
        
        names = [outcome['name'] for outcome in data['outcomes']]
        assert "Python Programming" in names
        assert "Data Analysis" in names
        assert "Team Leadership" not in names
    
    def test_get_outcomes_filter_category(self, client, app_context):
        """Test GET /api/outcomes with category filter."""
        # Create test outcomes
        outcome1 = LDOutcome(name="Test 1", description="Test", category="Knowledge", level="Basic")
        outcome2 = LDOutcome(name="Test 2", description="Test", category="Skills", level="Intermediate")
        outcome3 = LDOutcome(name="Test 3", description="Test", category="Behavior", level="Advanced")
        
        db.session.add_all([outcome1, outcome2, outcome3])
        db.session.commit()
        
        # Test filter by category
        response = client.get('/api/outcomes?category=Skills')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert len(data['outcomes']) == 1
        assert data['outcomes'][0]['category'] == 'Skills'
    
    def test_get_outcomes_filter_level(self, client, app_context):
        """Test GET /api/outcomes with level filter."""
        # Create test outcomes
        outcome1 = LDOutcome(name="Test 1", description="Test", category="Knowledge", level="Basic")
        outcome2 = LDOutcome(name="Test 2", description="Test", category="Skills", level="Intermediate")
        outcome3 = LDOutcome(name="Test 3", description="Test", category="Behavior", level="Advanced")
        
        db.session.add_all([outcome1, outcome2, outcome3])
        db.session.commit()
        
        # Test filter by level
        response = client.get('/api/outcomes?level=Advanced')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert len(data['outcomes']) == 1
        assert data['outcomes'][0]['level'] == 'Advanced'
    
    def test_get_outcomes_combined_filters(self, client, app_context):
        """Test GET /api/outcomes with multiple filters."""
        # Create test outcomes
        outcome1 = LDOutcome(name="Python Basics", description="Learn Python basics", 
                           category="Skills", level="Basic")
        outcome2 = LDOutcome(name="Advanced Python", description="Advanced Python programming", 
                           category="Skills", level="Advanced")
        outcome3 = LDOutcome(name="Leadership Skills", description="Leadership development", 
                           category="Behavior", level="Advanced")
        
        db.session.add_all([outcome1, outcome2, outcome3])
        db.session.commit()
        
        # Test combined filters
        response = client.get('/api/outcomes?category=Skills&level=Advanced&search=Python')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert len(data['outcomes']) == 1
        assert data['outcomes'][0]['name'] == 'Advanced Python'
    
    def test_get_outcome_by_id(self, client, app_context, sample_outcome):
        """Test GET /api/outcomes/<id>."""
        response = client.get(f'/api/outcomes/{sample_outcome.id}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['id'] == sample_outcome.id
        assert data['name'] == sample_outcome.name
        assert data['description'] == sample_outcome.description
    
    def test_get_outcome_by_invalid_id(self, client, app_context):
        """Test GET /api/outcomes/<id> with invalid ID."""
        response = client.get('/api/outcomes/999')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert 'error' in data
        assert 'not found' in data['error'].lower()


@pytest.mark.unit
@pytest.mark.api
class TestMetricTypesAPI:
    """Test metric types API endpoints."""
    
    def test_get_metric_types_empty(self, client, app_context):
        """Test GET /api/types with no data."""
        response = client.get('/api/types')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'metric_types' in data
        assert isinstance(data['metric_types'], list)
    
    def test_get_metric_types_with_data(self, client, app_context, sample_metric_type):
        """Test GET /api/types with data."""
        response = client.get('/api/types')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'metric_types' in data
        assert len(data['metric_types']) >= 1
        
        # Find our test metric type
        test_type = next((mt for mt in data['metric_types'] if mt['id'] == sample_metric_type.id), None)
        assert test_type is not None
        assert test_type['name'] == sample_metric_type.name
        assert test_type['description'] == sample_metric_type.description
        assert test_type['category'] == sample_metric_type.category
    
    def test_get_metric_types_filter_category(self, client, app_context):
        """Test GET /api/types with category filter."""
        # Create test metric types
        type1 = MetricType(name="Test Type 1", description="Test", category="Assessment")
        type2 = MetricType(name="Test Type 2", description="Test", category="Engagement")
        type3 = MetricType(name="Test Type 3", description="Test", category="Performance")
        
        db.session.add_all([type1, type2, type3])
        db.session.commit()
        
        # Test filter by category
        response = client.get('/api/types?category=Engagement')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        engagement_types = [mt for mt in data['metric_types'] if mt['category'] == 'Engagement']
        assert len(engagement_types) >= 1
    
    def test_get_metric_type_by_id(self, client, app_context, sample_metric_type):
        """Test GET /api/types/<id>."""
        response = client.get(f'/api/types/{sample_metric_type.id}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['id'] == sample_metric_type.id
        assert data['name'] == sample_metric_type.name
        assert data['description'] == sample_metric_type.description
    
    def test_get_metric_type_by_invalid_id(self, client, app_context):
        """Test GET /api/types/<id> with invalid ID."""
        response = client.get('/api/types/999')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert 'error' in data
        assert 'not found' in data['error'].lower()


@pytest.mark.unit
@pytest.mark.api
class TestMetricsAPI:
    """Test metrics API endpoints."""
    
    def test_get_metrics_empty(self, client, app_context):
        """Test GET /api/metrics with no data."""
        response = client.get('/api/metrics')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'metrics' in data
        assert isinstance(data['metrics'], list)
        assert len(data['metrics']) == 0
    
    def test_get_metrics_with_data(self, client, app_context, sample_metric):
        """Test GET /api/metrics with data."""
        response = client.get('/api/metrics')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'metrics' in data
        assert len(data['metrics']) == 1
        
        metric_data = data['metrics'][0]
        assert metric_data['id'] == sample_metric.id
        assert metric_data['name'] == sample_metric.name
        assert metric_data['description'] == sample_metric.description
        assert metric_data['outcome_id'] == sample_metric.outcome_id
        assert metric_data['metric_type_id'] == sample_metric.metric_type_id
    
    def test_get_metrics_filter_outcome(self, client, app_context, sample_outcome, sample_metric_type):
        """Test GET /api/metrics with outcome filter."""
        # Create another outcome and metrics
        outcome2 = LDOutcome(name="Other Outcome", description="Other", category="Skills", level="Basic")
        db.session.add(outcome2)
        db.session.commit()
        
        metric1 = Metric(name="Metric 1", description="Test", outcome_id=sample_outcome.id,
                        metric_type_id=sample_metric_type.id, measurement_method="Survey",
                        data_collection="Monthly", success_criteria="80%")
        metric2 = Metric(name="Metric 2", description="Test", outcome_id=outcome2.id,
                        metric_type_id=sample_metric_type.id, measurement_method="Analytics",
                        data_collection="Daily", success_criteria="90%")
        
        db.session.add_all([metric1, metric2])
        db.session.commit()
        
        # Test filter by outcome
        response = client.get(f'/api/metrics?outcome_id={sample_outcome.id}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert len(data['metrics']) == 1
        assert data['metrics'][0]['outcome_id'] == sample_outcome.id
    
    def test_get_metrics_filter_type(self, client, app_context, sample_outcome, sample_metric_type):
        """Test GET /api/metrics with metric type filter."""
        # Create another metric type and metrics
        type2 = MetricType(name="Other Type", description="Other", category="Performance")
        db.session.add(type2)
        db.session.commit()
        
        metric1 = Metric(name="Metric 1", description="Test", outcome_id=sample_outcome.id,
                        metric_type_id=sample_metric_type.id, measurement_method="Survey",
                        data_collection="Monthly", success_criteria="80%")
        metric2 = Metric(name="Metric 2", description="Test", outcome_id=sample_outcome.id,
                        metric_type_id=type2.id, measurement_method="Analytics",
                        data_collection="Daily", success_criteria="90%")
        
        db.session.add_all([metric1, metric2])
        db.session.commit()
        
        # Test filter by metric type
        response = client.get(f'/api/metrics?metric_type_id={sample_metric_type.id}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert len(data['metrics']) == 1
        assert data['metrics'][0]['metric_type_id'] == sample_metric_type.id
    
    def test_get_metric_by_id(self, client, app_context, sample_metric):
        """Test GET /api/metrics/<id>."""
        response = client.get(f'/api/metrics/{sample_metric.id}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['id'] == sample_metric.id
        assert data['name'] == sample_metric.name
        assert data['description'] == sample_metric.description
        assert 'outcome' in data
        assert 'metric_type' in data
    
    def test_get_metric_by_invalid_id(self, client, app_context):
        """Test GET /api/metrics/<id> with invalid ID."""
        response = client.get('/api/metrics/999')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert 'error' in data
        assert 'not found' in data['error'].lower()


@pytest.mark.unit
@pytest.mark.api
class TestTranslatorAPI:
    """Test translator API endpoints."""
    
    def test_translate_valid_request(self, client, app_context, sample_outcome, sample_metric_type):
        """Test POST /api/translate with valid data."""
        data = {
            'outcome_id': sample_outcome.id,
            'metric_type_id': sample_metric_type.id,
            'additional_context': 'Test context for translation'
        }
        
        response = client.post('/api/translate', 
                             data=json.dumps(data),
                             content_type='application/json')
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'suggestions' in result
        assert isinstance(result['suggestions'], list)
        assert len(result['suggestions']) > 0
        
        # Check suggestion structure
        suggestion = result['suggestions'][0]
        assert 'name' in suggestion
        assert 'description' in suggestion
        assert 'measurement_method' in suggestion
        assert 'data_collection' in suggestion
        assert 'success_criteria' in suggestion
    
    def test_translate_invalid_outcome(self, client, app_context, sample_metric_type):
        """Test POST /api/translate with invalid outcome ID."""
        data = {
            'outcome_id': 999,  # Invalid ID
            'metric_type_id': sample_metric_type.id,
            'additional_context': 'Test context'
        }
        
        response = client.post('/api/translate',
                             data=json.dumps(data),
                             content_type='application/json')
        assert response.status_code == 400
        
        result = json.loads(response.data)
        assert 'error' in result
        assert 'outcome' in result['error'].lower()
    
    def test_translate_invalid_metric_type(self, client, app_context, sample_outcome):
        """Test POST /api/translate with invalid metric type ID."""
        data = {
            'outcome_id': sample_outcome.id,
            'metric_type_id': 999,  # Invalid ID
            'additional_context': 'Test context'
        }
        
        response = client.post('/api/translate',
                             data=json.dumps(data),
                             content_type='application/json')
        assert response.status_code == 400
        
        result = json.loads(response.data)
        assert 'error' in result
        assert 'metric type' in result['error'].lower()
    
    def test_translate_missing_data(self, client, app_context):
        """Test POST /api/translate with missing required data."""
        data = {
            'additional_context': 'Test context'
            # Missing outcome_id and metric_type_id
        }
        
        response = client.post('/api/translate',
                             data=json.dumps(data),
                             content_type='application/json')
        assert response.status_code == 400
        
        result = json.loads(response.data)
        assert 'error' in result
    
    def test_translate_invalid_json(self, client, app_context):
        """Test POST /api/translate with invalid JSON."""
        response = client.post('/api/translate',
                             data='invalid json',
                             content_type='application/json')
        assert response.status_code == 400
        
        result = json.loads(response.data)
        assert 'error' in result


@pytest.mark.unit
@pytest.mark.api
class TestAPIErrorHandling:
    """Test API error handling."""
    
    def test_api_404_error(self, client):
        """Test API 404 error handling."""
        response = client.get('/api/nonexistent')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert 'error' in data
        assert '404' in str(data['error']) or 'not found' in data['error'].lower()
    
    def test_api_method_not_allowed(self, client):
        """Test API method not allowed error."""
        response = client.post('/api/outcomes')  # GET only endpoint
        assert response.status_code == 405
        
        data = json.loads(response.data)
        assert 'error' in data
        assert 'method' in data['error'].lower() or '405' in str(data['error'])
    
    def test_api_content_type_error(self, client, app_context, sample_outcome, sample_metric_type):
        """Test API content type error."""
        data = {
            'outcome_id': sample_outcome.id,
            'metric_type_id': sample_metric_type.id
        }
        
        # Send without proper content type
        response = client.post('/api/translate', data=json.dumps(data))
        # Should handle gracefully or return appropriate error
        assert response.status_code in [400, 415]


@pytest.mark.unit
@pytest.mark.api
class TestAPIResponseFormat:
    """Test API response format consistency."""
    
    def test_outcomes_response_format(self, client, app_context, sample_outcome):
        """Test outcomes API response format."""
        response = client.get('/api/outcomes')
        assert response.status_code == 200
        assert response.content_type == 'application/json'
        
        data = json.loads(response.data)
        assert isinstance(data, dict)
        assert 'outcomes' in data
        assert isinstance(data['outcomes'], list)
        
        if data['outcomes']:
            outcome = data['outcomes'][0]
            required_fields = ['id', 'name', 'description', 'category', 'level', 'created_at']
            for field in required_fields:
                assert field in outcome
    
    def test_metric_types_response_format(self, client, app_context, sample_metric_type):
        """Test metric types API response format."""
        response = client.get('/api/types')
        assert response.status_code == 200
        assert response.content_type == 'application/json'
        
        data = json.loads(response.data)
        assert isinstance(data, dict)
        assert 'metric_types' in data
        assert isinstance(data['metric_types'], list)
    
    def test_metrics_response_format(self, client, app_context, sample_metric):
        """Test metrics API response format."""
        response = client.get('/api/metrics')
        assert response.status_code == 200
        assert response.content_type == 'application/json'
        
        data = json.loads(response.data)
        assert isinstance(data, dict)
        assert 'metrics' in data
        assert isinstance(data['metrics'], list)
        
        if data['metrics']:
            metric = data['metrics'][0]
            required_fields = ['id', 'name', 'description', 'outcome_id', 'metric_type_id', 'created_at']
            for field in required_fields:
                assert field in metric
    
    def test_error_response_format(self, client):
        """Test error response format consistency."""
        response = client.get('/api/outcomes/999')
        assert response.status_code == 404
        assert response.content_type == 'application/json'
        
        data = json.loads(response.data)
        assert isinstance(data, dict)
        assert 'error' in data
        assert isinstance(data['error'], str)


@pytest.mark.unit
@pytest.mark.api
class TestAPIPagination:
    """Test API pagination."""
    
    def test_outcomes_pagination(self, client, app_context):
        """Test outcomes API pagination."""
        # Create many outcomes
        outcomes = []
        for i in range(25):
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
        response = client.get('/api/outcomes?page=1&per_page=10')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert len(data['outcomes']) == 10
        
        # Test pagination metadata if implemented
        if 'pagination' in data:
            assert 'page' in data['pagination']
            assert 'per_page' in data['pagination']
            assert 'total' in data['pagination']
    
    def test_metrics_pagination(self, client, app_context, sample_outcome, sample_metric_type):
        """Test metrics API pagination."""
        # Create many metrics
        metrics = []
        for i in range(25):
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
        response = client.get('/api/metrics?page=1&per_page=10')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert len(data['metrics']) == 10
