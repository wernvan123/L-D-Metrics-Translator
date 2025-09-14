#!/usr/bin/env python3
"""
Test script for Event Analysis functionality
Tests database operations, API endpoints, and data integrity
"""

import sys
import os
import json
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import EventAnalysis
from app.database import (
    create_event_analysis, 
    get_recent_event_analyses, 
    get_event_analysis_by_id,
    search_event_analyses,
    delete_event_analysis
)

def test_database_operations():
    """Test all CRUD operations for EventAnalysis."""
    print("Testing Event Analysis Database Operations")
    print("=" * 50)
    
    app = create_app()
    with app.app_context():
        # Ensure tables exist
        db.create_all()
        
        # Test 1: Create event analysis
        print("\n1. Testing create_event_analysis...")
        try:
            analysis = create_event_analysis(
                event_description="Team struggled with remote collaboration tools",
                analysis_result='{"learning_needs": ["Digital literacy", "Communication skills"], "recommended_metrics": ["Tool adoption rate", "Collaboration effectiveness"]}',
                generated_by="test_ai",
                success=True,
                ip_address="127.0.0.1"
            )
            print(f"PASS: Created analysis with ID: {analysis.id}")
        except Exception as e:
            print(f"FAIL: Failed to create analysis: {e}")
            return False
        
        # Test 2: Get recent analyses
        print("\n2. Testing get_recent_event_analyses...")
        try:
            recent = get_recent_event_analyses(limit=5)
            print(f"PASS: Retrieved {len(recent)} recent analyses")
            for r in recent:
                print(f"   - ID: {r.id}, Description: {r.event_description[:50]}...")
        except Exception as e:
            print(f"FAIL: Failed to get recent analyses: {e}")
            return False
        
        # Test 3: Get by ID
        print("\n3. Testing get_event_analysis_by_id...")
        try:
            retrieved = get_event_analysis_by_id(analysis.id)
            if retrieved:
                print(f"PASS: Retrieved analysis: {retrieved.event_description[:50]}...")
            else:
                print("FAIL: Analysis not found")
                return False
        except Exception as e:
            print(f"FAIL: Failed to get analysis by ID: {e}")
            return False
        
        # Test 4: Search analyses
        print("\n4. Testing search_event_analyses...")
        try:
            results = search_event_analyses("collaboration", limit=10)
            print(f"PASS: Found {len(results)} analyses matching 'collaboration'")
        except Exception as e:
            print(f"FAIL: Failed to search analyses: {e}")
            return False
        
        # Test 5: Model methods
        print("\n5. Testing EventAnalysis model methods...")
        try:
            # Test to_dict method
            analysis_dict = analysis.to_dict()
            print(f"PASS: to_dict() returned {len(analysis_dict)} fields")
            
            # Test class methods
            recent_class = EventAnalysis.get_recent_searches(limit=3)
            print(f"PASS: EventAnalysis.get_recent_searches() returned {len(recent_class)} results")
            
            search_class = EventAnalysis.search_by_description("team")
            search_results = search_class.all()
            print(f"PASS: EventAnalysis.search_by_description() returned {len(search_results)} results")
            
        except Exception as e:
            print(f"FAIL: Failed model method tests: {e}")
            return False
        
        # Test 6: Delete analysis (cleanup)
        print("\n6. Testing delete_event_analysis...")
        try:
            deleted = delete_event_analysis(analysis.id)
            if deleted:
                print("PASS: Successfully deleted test analysis")
            else:
                print("FAIL: Failed to delete analysis")
                return False
        except Exception as e:
            print(f"FAIL: Failed to delete analysis: {e}")
            return False
        
        print("\nAll database tests passed!")
        return True

def test_api_endpoints():
    """Test API endpoints for event analysis."""
    print("\nTesting Event Analysis API Endpoints")
    print("=" * 50)
    
    app = create_app()
    client = app.test_client()
    
    with app.app_context():
        db.create_all()
        
        # Test 1: Analyze event endpoint
        print("\n1. Testing POST /api/analyze-event...")
        try:
            response = client.post('/api/analyze-event', 
                                 json={'event_description': 'Test event for API testing'},
                                 content_type='application/json')
            
            print(f"   Status Code: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                print(f"   Success: {data.get('success')}")
                print(f"   Generated by: {data.get('generated_by')}")
                print("PASS: Analyze event endpoint working")
            else:
                print(f"FAIL: Analyze event failed: {response.get_data(as_text=True)}")
                return False
        except Exception as e:
            print(f"FAIL: Failed to test analyze event: {e}")
            return False
        
        # Test 2: Get recent analyses endpoint
        print("\n2. Testing GET /api/event-analyses/recent...")
        try:
            response = client.get('/api/event-analyses/recent?limit=5')
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.get_json()
                print(f"   Success: {data.get('success')}")
                print(f"   Count: {data.get('count')}")
                print("PASS: Recent analyses endpoint working")
            else:
                print(f"FAIL: Recent analyses failed: {response.get_data(as_text=True)}")
                return False
        except Exception as e:
            print(f"FAIL: Failed to test recent analyses: {e}")
            return False
        
        print("\nAll API tests passed!")
        return True

def main():
    """Run all tests."""
    print("Starting Event Analysis Tests")
    print("=" * 60)
    
    # Test database operations
    db_success = test_database_operations()
    
    # Test API endpoints
    api_success = test_api_endpoints()
    
    # Final results
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Database Operations: {'PASSED' if db_success else 'FAILED'}")
    print(f"API Endpoints: {'PASSED' if api_success else 'FAILED'}")
    
    if db_success and api_success:
        print("\nALL TESTS PASSED! Event Analysis functionality is working correctly.")
        return True
    else:
        print("\nSOME TESTS FAILED! Please check the implementation.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
