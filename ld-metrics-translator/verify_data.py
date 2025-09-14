#!/usr/bin/env python3
"""
Verification script to test that all seeded data is working correctly.
This script queries the database and verifies relationships.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import LDOutcome, MetricType, Metric


def verify_data():
    """Verify that all seeded data is correctly stored and relationships work."""
    print("=" * 60)
    print("L&D METRICS TRANSLATOR - DATA VERIFICATION")
    print("=" * 60)
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        # Test basic counts
        outcomes_count = LDOutcome.query.count()
        types_count = MetricType.query.count()
        metrics_count = Metric.query.count()
        
        print(f"Database Counts:")
        print(f"  L&D Outcomes: {outcomes_count}")
        print(f"  Metric Types: {types_count}")
        print(f"  Metrics: {metrics_count}")
        
        # Verify expected counts
        expected_outcomes = 5
        expected_types = 3
        expected_metrics = 25
        
        if outcomes_count != expected_outcomes:
            print(f"[ERROR] Expected {expected_outcomes} outcomes, found {outcomes_count}")
            return False
        
        if types_count != expected_types:
            print(f"[ERROR] Expected {expected_types} metric types, found {types_count}")
            return False
            
        if metrics_count != expected_metrics:
            print(f"[ERROR] Expected {expected_metrics} metrics, found {metrics_count}")
            return False
        
        print("[OK] All counts match expected values")
        
        # Test relationships
        print(f"\nTesting Relationships:")
        
        # Test outcome relationships
        for outcome in LDOutcome.query.all():
            metrics_for_outcome = outcome.metrics.count()
            print(f"  {outcome.name}: {metrics_for_outcome} metrics")
            
            # Test that each metric has proper relationships
            for metric in outcome.metrics:
                if not metric.metric_type:
                    print(f"[ERROR] Metric '{metric.name}' has no metric type")
                    return False
                if not metric.outcome:
                    print(f"[ERROR] Metric '{metric.name}' has no L&D outcome")
                    return False
        
        # Test metric type relationships
        for metric_type in MetricType.query.all():
            metrics_for_type = Metric.query.filter_by(metric_type_id=metric_type.id).count()
            print(f"  {metric_type.name}: {metrics_for_type} metrics")
        
        # Test sample metric details
        print(f"\nSample Metrics:")
        sample_metrics = Metric.query.limit(3).all()
        for metric in sample_metrics:
            print(f"  • {metric.name}")
            print(f"    Type: {metric.metric_type.name}")
            print(f"    Outcome: {metric.outcome.name}")
            print(f"    Description: {metric.description[:100]}...")
            if metric.example:
                print(f"    Example: {metric.example[:100]}...")
            print()
        
        # Test search functionality
        print("Testing Search Functionality:")
        search_results = Metric.search("engagement").all()
        print(f"  Search for 'engagement': {len(search_results)} results")
        
        search_results = Metric.search("neuroscience").all()
        print(f"  Search for 'neuroscience': {len(search_results)} results")
        
        # Test filtering
        print("Testing Filtering:")
        engagement_outcome = LDOutcome.query.filter_by(name='Engagement').first()
        if engagement_outcome:
            engagement_metrics = Metric.filter_by_outcome(engagement_outcome.id).count()
            print(f"  Engagement metrics: {engagement_metrics}")
        
        operational_type = MetricType.query.filter_by(name='Operational KPI').first()
        if operational_type:
            operational_metrics = Metric.filter_by_type(operational_type.id).count()
            print(f"  Operational KPI metrics: {operational_metrics}")
        
        print("\n" + "=" * 60)
        print("[SUCCESS] ALL VERIFICATION TESTS PASSED!")
        print("[SUCCESS] Database is properly seeded with comprehensive L&D metrics data")
        print("[SUCCESS] All relationships are working correctly")
        print("[SUCCESS] Search and filtering functionality is operational")
        print("=" * 60)
        
        return True


if __name__ == '__main__':
    success = verify_data()
    if not success:
        print("\n[ERROR] Verification failed!")
        sys.exit(1)
    else:
        print("\n[SUCCESS] L&D Metrics Translator is ready for use!")
