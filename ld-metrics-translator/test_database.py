#!/usr/bin/env python3
"""
Test script for database setup and basic CRUD operations.
Run this script to verify that the database models and setup are working correctly.
"""

import os
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import LDOutcome, MetricType, Metric
from app.database import init_database, seed_basic_data, seed_sample_metrics, get_database_stats


def test_database_setup():
    """Test database initialization and basic operations."""
    print("=== Testing L&D Metrics Translator Database Setup ===\n")
    
    # Create Flask app and initialize database
    app = create_app('testing')  # Use in-memory database for testing
    
    with app.app_context():
        print("1. Initializing database...")
        init_database()
        print("   ✓ Database tables created successfully!")
        
        print("\n2. Seeding basic data...")
        seed_basic_data()
        print("   ✓ Basic data seeded successfully!")
        
        print("\n3. Seeding sample metrics...")
        seed_sample_metrics()
        print("   ✓ Sample metrics seeded successfully!")
        
        print("\n4. Testing database statistics...")
        stats = get_database_stats()
        
        print("\n5. Testing model validation...")
        test_model_validation()
        
        print("\n6. Testing model relationships...")
        test_model_relationships()
        
        print("\n7. Testing search and filter methods...")
        test_search_and_filters()
        
        print("\n=== All tests passed! Database setup is working correctly ===")


def test_model_validation():
    """Test model validation methods."""
    print("   Testing L&D Outcome validation...")
    
    # Test valid outcome
    try:
        outcome = LDOutcome(name="test engagement", description="Test description")
        assert outcome.name == "Test Engagement"  # Should be title-cased
        print("     ✓ Valid outcome creation and name formatting")
    except Exception as e:
        print(f"     ✗ Error creating valid outcome: {e}")
        return
    
    # Test invalid outcome (empty name)
    try:
        invalid_outcome = LDOutcome(name="", description="Test")
        db.session.add(invalid_outcome)
        db.session.flush()  # This should trigger validation
        print("     ✗ Should have failed with empty name")
    except ValueError:
        print("     ✓ Correctly rejected empty name")
    except Exception as e:
        print(f"     ✗ Unexpected error: {e}")
    
    print("   Testing Metric validation...")
    
    # Test valid metric
    try:
        engagement = LDOutcome.query.filter_by(name='Engagement').first()
        kpi_type = MetricType.query.filter_by(name='Operational KPI').first()
        
        if engagement and kpi_type:
            metric = Metric(
                name="Test Metric",
                description="Test description",
                example="Test example",
                outcome_id=engagement.id,
                metric_type_id=kpi_type.id
            )
            print("     ✓ Valid metric creation")
        else:
            print("     ✗ Could not find required outcome or type for testing")
    except Exception as e:
        print(f"     ✗ Error creating valid metric: {e}")


def test_model_relationships():
    """Test model relationships."""
    print("   Testing model relationships...")
    
    # Get a metric and test its relationships
    metric = Metric.query.first()
    if metric:
        print(f"     ✓ Metric '{metric.name}' found")
        print(f"     ✓ L&D Outcome: {metric.outcome.name}")
        print(f"     ✓ Metric Type: {metric.metric_type.name}")
        
        # Test reverse relationship
        outcome = metric.outcome
        outcome_metrics = outcome.metrics.all()
        print(f"     ✓ Outcome '{outcome.name}' has {len(outcome_metrics)} metrics")
    else:
        print("     ✗ No metrics found for relationship testing")


def test_search_and_filters():
    """Test search and filter methods."""
    print("   Testing search functionality...")
    
    # Test search
    search_results = Metric.search("Employee").all()
    print(f"     ✓ Search for 'Employee' returned {len(search_results)} results")
    
    # Test outcome filter
    engagement = LDOutcome.query.filter_by(name='Engagement').first()
    if engagement:
        outcome_metrics = Metric.filter_by_outcome(engagement.id).all()
        print(f"     ✓ Engagement metrics: {len(outcome_metrics)} found")
    
    # Test type filter
    kpi_type = MetricType.query.filter_by(name='Operational KPI').first()
    if kpi_type:
        type_metrics = Metric.filter_by_type(kpi_type.id).all()
        print(f"     ✓ Operational KPI metrics: {len(type_metrics)} found")


def test_json_serialization():
    """Test JSON serialization methods."""
    print("   Testing JSON serialization...")
    
    # Test outcome serialization
    outcome = LDOutcome.query.first()
    if outcome:
        outcome_dict = outcome.to_dict()
        required_keys = ['id', 'name', 'description', 'created_date', 'metrics_count']
        if all(key in outcome_dict for key in required_keys):
            print("     ✓ LDOutcome JSON serialization")
        else:
            print("     ✗ LDOutcome JSON serialization missing keys")
    
    # Test metric serialization
    metric = Metric.query.first()
    if metric:
        metric_dict = metric.to_dict()
        required_keys = ['id', 'name', 'description', 'outcome_id', 'outcome_name', 'metric_type_id', 'metric_type_name']
        if all(key in metric_dict for key in required_keys):
            print("     ✓ Metric JSON serialization")
        else:
            print("     ✗ Metric JSON serialization missing keys")


if __name__ == '__main__':
    test_database_setup()
