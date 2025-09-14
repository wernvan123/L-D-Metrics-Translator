"""
Unit tests for database models.
"""
import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.models import LDOutcome, MetricType, Metric, User
from app import db


@pytest.mark.unit
@pytest.mark.database
class TestLDOutcome:
    """Test LDOutcome model."""
    
    def test_create_outcome(self, app_context):
        """Test creating a new outcome."""
        outcome = LDOutcome(
            name="Test Outcome",
            description="Test description",
            category="Knowledge",
            level="Basic"
        )
        db.session.add(outcome)
        db.session.commit()
        
        assert outcome.id is not None
        assert outcome.name == "Test Outcome"
        assert outcome.category == "Knowledge"
        assert outcome.level == "Basic"
        assert outcome.created_at is not None
    
    def test_outcome_validation(self, app_context):
        """Test outcome validation methods."""
        outcome = LDOutcome(
            name="Test Outcome",
            description="Test description",
            category="Knowledge",
            level="Basic"
        )
        
        assert outcome.is_valid_category()
        assert outcome.is_valid_level()
        
        # Test invalid category
        outcome.category = "Invalid"
        assert not outcome.is_valid_category()
        
        # Test invalid level
        outcome.category = "Knowledge"
        outcome.level = "Invalid"
        assert not outcome.is_valid_level()
    
    def test_outcome_json_serialization(self, app_context, sample_outcome):
        """Test JSON serialization."""
        json_data = sample_outcome.to_dict()
        
        assert json_data['id'] == sample_outcome.id
        assert json_data['name'] == sample_outcome.name
        assert json_data['description'] == sample_outcome.description
        assert json_data['category'] == sample_outcome.category
        assert json_data['level'] == sample_outcome.level
        assert 'created_at' in json_data
    
    def test_outcome_search(self, app_context):
        """Test outcome search functionality."""
        # Create test outcomes
        outcome1 = LDOutcome(name="Python Programming", description="Learn Python", category="Skills", level="Intermediate")
        outcome2 = LDOutcome(name="Data Analysis", description="Analyze data with Python", category="Skills", level="Advanced")
        outcome3 = LDOutcome(name="Team Leadership", description="Lead teams effectively", category="Behavior", level="Advanced")
        
        db.session.add_all([outcome1, outcome2, outcome3])
        db.session.commit()
        
        # Test search by name
        results = LDOutcome.search("Python")
        assert len(results) == 2
        
        # Test search by description
        results = LDOutcome.search("teams")
        assert len(results) == 1
        assert results[0].name == "Team Leadership"
    
    def test_outcome_filtering(self, app_context):
        """Test outcome filtering."""
        # Create test outcomes
        outcome1 = LDOutcome(name="Test 1", description="Test", category="Knowledge", level="Basic")
        outcome2 = LDOutcome(name="Test 2", description="Test", category="Skills", level="Intermediate")
        outcome3 = LDOutcome(name="Test 3", description="Test", category="Behavior", level="Advanced")
        
        db.session.add_all([outcome1, outcome2, outcome3])
        db.session.commit()
        
        # Test filter by category
        results = LDOutcome.filter_by_category("Skills")
        assert len(results) == 1
        assert results[0].category == "Skills"
        
        # Test filter by level
        results = LDOutcome.filter_by_level("Advanced")
        assert len(results) == 1
        assert results[0].level == "Advanced"


@pytest.mark.unit
@pytest.mark.database
class TestMetricType:
    """Test MetricType model."""
    
    def test_create_metric_type(self, app_context):
        """Test creating a new metric type."""
        metric_type = MetricType(
            name="Test Metric Type",
            description="Test description",
            category="Assessment"
        )
        db.session.add(metric_type)
        db.session.commit()
        
        assert metric_type.id is not None
        assert metric_type.name == "Test Metric Type"
        assert metric_type.category == "Assessment"
        assert metric_type.created_at is not None
    
    def test_metric_type_validation(self, app_context):
        """Test metric type validation."""
        metric_type = MetricType(
            name="Test Type",
            description="Test description",
            category="Assessment"
        )
        
        assert metric_type.is_valid_category()
        
        # Test invalid category
        metric_type.category = "Invalid"
        assert not metric_type.is_valid_category()
    
    def test_metric_type_json_serialization(self, app_context, sample_metric_type):
        """Test JSON serialization."""
        json_data = sample_metric_type.to_dict()
        
        assert json_data['id'] == sample_metric_type.id
        assert json_data['name'] == sample_metric_type.name
        assert json_data['description'] == sample_metric_type.description
        assert json_data['category'] == sample_metric_type.category
        assert 'created_at' in json_data


@pytest.mark.unit
@pytest.mark.database
class TestMetric:
    """Test Metric model."""
    
    def test_create_metric(self, app_context, sample_outcome, sample_metric_type):
        """Test creating a new metric."""
        metric = Metric(
            name="Test Metric",
            description="Test description",
            outcome_id=sample_outcome.id,
            metric_type_id=sample_metric_type.id,
            measurement_method="Survey",
            data_collection="Monthly",
            success_criteria="80% completion"
        )
        db.session.add(metric)
        db.session.commit()
        
        assert metric.id is not None
        assert metric.name == "Test Metric"
        assert metric.outcome_id == sample_outcome.id
        assert metric.metric_type_id == sample_metric_type.id
        assert metric.created_at is not None
    
    def test_metric_relationships(self, app_context, sample_metric):
        """Test metric relationships."""
        assert sample_metric.outcome is not None
        assert sample_metric.metric_type is not None
        assert sample_metric.outcome.name == "Test Outcome"
        assert sample_metric.metric_type.name == "Test Metric Type"
    
    def test_metric_validation(self, app_context, sample_outcome, sample_metric_type):
        """Test metric validation."""
        metric = Metric(
            name="Test Metric",
            description="Test description",
            outcome_id=sample_outcome.id,
            metric_type_id=sample_metric_type.id,
            measurement_method="Survey",
            data_collection="Monthly",
            success_criteria="80% completion"
        )
        
        assert metric.is_valid_measurement_method()
        assert metric.is_valid_data_collection()
        
        # Test invalid measurement method
        metric.measurement_method = "Invalid"
        assert not metric.is_valid_measurement_method()
        
        # Test invalid data collection
        metric.measurement_method = "Survey"
        metric.data_collection = "Invalid"
        assert not metric.is_valid_data_collection()
    
    def test_metric_json_serialization(self, app_context, sample_metric):
        """Test JSON serialization."""
        json_data = sample_metric.to_dict()
        
        assert json_data['id'] == sample_metric.id
        assert json_data['name'] == sample_metric.name
        assert json_data['description'] == sample_metric.description
        assert json_data['outcome_id'] == sample_metric.outcome_id
        assert json_data['metric_type_id'] == sample_metric.metric_type_id
        assert 'created_at' in json_data
    
    def test_metric_search(self, app_context, sample_outcome, sample_metric_type):
        """Test metric search functionality."""
        # Create test metrics
        metric1 = Metric(name="Completion Rate", description="Course completion", 
                        outcome_id=sample_outcome.id, metric_type_id=sample_metric_type.id,
                        measurement_method="Analytics", data_collection="Daily", success_criteria="90%")
        metric2 = Metric(name="Satisfaction Score", description="Student satisfaction", 
                        outcome_id=sample_outcome.id, metric_type_id=sample_metric_type.id,
                        measurement_method="Survey", data_collection="Weekly", success_criteria="4.0/5.0")
        
        db.session.add_all([metric1, metric2])
        db.session.commit()
        
        # Test search by name
        results = Metric.search("Completion")
        assert len(results) == 1
        assert results[0].name == "Completion Rate"
        
        # Test search by description
        results = Metric.search("satisfaction")
        assert len(results) == 1
        assert results[0].name == "Satisfaction Score"


@pytest.mark.unit
@pytest.mark.database
class TestUser:
    """Test User model."""
    
    def test_create_user(self, app_context):
        """Test creating a new user."""
        user = User(
            username="testuser",
            email="test@example.com",
            is_admin=False
        )
        user.set_password("testpassword")
        db.session.add(user)
        db.session.commit()
        
        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert not user.is_admin
        assert user.created_at is not None
    
    def test_password_hashing(self, app_context):
        """Test password hashing and verification."""
        user = User(username="testuser", email="test@example.com")
        user.set_password("testpassword")
        
        assert user.password_hash is not None
        assert user.password_hash != "testpassword"
        assert user.check_password("testpassword")
        assert not user.check_password("wrongpassword")
    
    def test_user_json_serialization(self, app_context, admin_user):
        """Test JSON serialization."""
        json_data = admin_user.to_dict()
        
        assert json_data['id'] == admin_user.id
        assert json_data['username'] == admin_user.username
        assert json_data['email'] == admin_user.email
        assert json_data['is_admin'] == admin_user.is_admin
        assert 'password_hash' not in json_data  # Should not expose password
        assert 'created_at' in json_data
    
    def test_unique_constraints(self, app_context):
        """Test unique constraints on username and email."""
        user1 = User(username="testuser", email="test@example.com")
        user1.set_password("password")
        db.session.add(user1)
        db.session.commit()
        
        # Test duplicate username
        user2 = User(username="testuser", email="different@example.com")
        user2.set_password("password")
        db.session.add(user2)
        
        with pytest.raises(IntegrityError):
            db.session.commit()
        
        db.session.rollback()
        
        # Test duplicate email
        user3 = User(username="different", email="test@example.com")
        user3.set_password("password")
        db.session.add(user3)
        
        with pytest.raises(IntegrityError):
            db.session.commit()


@pytest.mark.unit
@pytest.mark.database
class TestModelRelationships:
    """Test model relationships and cascading."""
    
    def test_outcome_metrics_relationship(self, app_context, sample_outcome, sample_metric_type):
        """Test one-to-many relationship between outcomes and metrics."""
        # Create multiple metrics for the same outcome
        metric1 = Metric(name="Metric 1", description="Test", outcome_id=sample_outcome.id,
                        metric_type_id=sample_metric_type.id, measurement_method="Survey",
                        data_collection="Monthly", success_criteria="80%")
        metric2 = Metric(name="Metric 2", description="Test", outcome_id=sample_outcome.id,
                        metric_type_id=sample_metric_type.id, measurement_method="Analytics",
                        data_collection="Daily", success_criteria="90%")
        
        db.session.add_all([metric1, metric2])
        db.session.commit()
        
        # Test relationship
        assert len(sample_outcome.metrics) == 2
        assert metric1 in sample_outcome.metrics
        assert metric2 in sample_outcome.metrics
    
    def test_metric_type_metrics_relationship(self, app_context, sample_outcome, sample_metric_type):
        """Test one-to-many relationship between metric types and metrics."""
        # Create multiple metrics for the same metric type
        metric1 = Metric(name="Metric 1", description="Test", outcome_id=sample_outcome.id,
                        metric_type_id=sample_metric_type.id, measurement_method="Survey",
                        data_collection="Monthly", success_criteria="80%")
        metric2 = Metric(name="Metric 2", description="Test", outcome_id=sample_outcome.id,
                        metric_type_id=sample_metric_type.id, measurement_method="Analytics",
                        data_collection="Daily", success_criteria="90%")
        
        db.session.add_all([metric1, metric2])
        db.session.commit()
        
        # Test relationship
        assert len(sample_metric_type.metrics) == 2
        assert metric1 in sample_metric_type.metrics
        assert metric2 in sample_metric_type.metrics
    
    def test_cascade_delete(self, app_context, sample_outcome, sample_metric_type):
        """Test cascade delete behavior."""
        # Create a metric
        metric = Metric(name="Test Metric", description="Test", outcome_id=sample_outcome.id,
                       metric_type_id=sample_metric_type.id, measurement_method="Survey",
                       data_collection="Monthly", success_criteria="80%")
        db.session.add(metric)
        db.session.commit()
        
        metric_id = metric.id
        
        # Delete the outcome
        db.session.delete(sample_outcome)
        db.session.commit()
        
        # Metric should be deleted due to cascade
        deleted_metric = Metric.query.get(metric_id)
        assert deleted_metric is None
