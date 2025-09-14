#!/usr/bin/env python3
"""
Test script for L&D Metrics Translator API endpoints.
This script tests all API endpoints with various filter combinations and edge cases.
"""

import requests
import json
import sys
from urllib.parse import urlencode

# Base URL for the API
BASE_URL = "http://127.0.0.1:5000/api"

def print_test_result(test_name, success, details=""):
    """Print formatted test results."""
    status = "[PASS]" if success else "[FAIL]"
    print(f"{status} {test_name}")
    if details:
        print(f"    {details}")
    print()

def test_endpoint(endpoint, expected_status=200, params=None):
    """Test an API endpoint and return the response."""
    url = f"{BASE_URL}{endpoint}"
    if params:
        url += "?" + urlencode(params)
    
    try:
        response = requests.get(url)
        return response.status_code, response.json() if response.content else None
    except Exception as e:
        return None, str(e)

def main():
    """Run all API endpoint tests."""
    print("=" * 60)
    print("L&D METRICS TRANSLATOR API ENDPOINT TESTS")
    print("=" * 60)
    print()
    
    # Test 1: GET /api/outcomes
    print("1. Testing /api/outcomes endpoint")
    status, data = test_endpoint("/outcomes")
    success = status == 200 and data and "outcomes" in data
    details = f"Status: {status}, Outcomes count: {len(data.get('outcomes', [])) if data else 'N/A'}"
    print_test_result("GET /api/outcomes", success, details)
    
    # Test 2: GET /api/types
    print("2. Testing /api/types endpoint")
    status, data = test_endpoint("/types")
    success = status == 200 and data and "types" in data
    details = f"Status: {status}, Types count: {len(data.get('types', [])) if data else 'N/A'}"
    print_test_result("GET /api/types", success, details)
    
    # Test 3: GET /api/metrics (basic)
    print("3. Testing /api/metrics endpoint (basic)")
    status, data = test_endpoint("/metrics")
    success = status == 200 and data and "metrics" in data and "pagination" in data
    details = f"Status: {status}, Metrics count: {len(data.get('metrics', [])) if data else 'N/A'}"
    print_test_result("GET /api/metrics", success, details)
    
    # Test 4: GET /api/metrics with outcome filter
    print("4. Testing /api/metrics with outcome filter")
    status, data = test_endpoint("/metrics", params={"outcome": 1})
    success = status == 200 and data and "metrics" in data
    engagement_metrics = len(data.get('metrics', [])) if data else 0
    details = f"Status: {status}, Engagement metrics: {engagement_metrics}"
    print_test_result("GET /api/metrics?outcome=1", success, details)
    
    # Test 5: GET /api/metrics with type filter
    print("5. Testing /api/metrics with type filter")
    status, data = test_endpoint("/metrics", params={"type": 1})
    success = status == 200 and data and "metrics" in data
    kpi_metrics = len(data.get('metrics', [])) if data else 0
    details = f"Status: {status}, Operational KPI metrics: {kpi_metrics}"
    print_test_result("GET /api/metrics?type=1", success, details)
    
    # Test 6: GET /api/metrics with combined filters
    print("6. Testing /api/metrics with combined filters")
    status, data = test_endpoint("/metrics", params={"outcome": 1, "type": 2})
    success = status == 200 and data and "metrics" in data
    combined_metrics = len(data.get('metrics', [])) if data else 0
    details = f"Status: {status}, Engagement + Behavioral metrics: {combined_metrics}"
    print_test_result("GET /api/metrics?outcome=1&type=2", success, details)
    
    # Test 7: GET /api/metrics with search query
    print("7. Testing /api/metrics with search query")
    status, data = test_endpoint("/metrics", params={"q": "productivity"})
    success = status == 200 and data and "metrics" in data
    search_results = len(data.get('metrics', [])) if data else 0
    details = f"Status: {status}, Search results for 'productivity': {search_results}"
    print_test_result("GET /api/metrics?q=productivity", success, details)
    
    # Test 8: GET /api/metrics/search
    print("8. Testing /api/metrics/search endpoint")
    status, data = test_endpoint("/metrics/search", params={"q": "employee"})
    success = status == 200 and data and "metrics" in data
    search_results = len(data.get('metrics', [])) if data else 0
    details = f"Status: {status}, Search results for 'employee': {search_results}"
    print_test_result("GET /api/metrics/search?q=employee", success, details)
    
    # Test 9: GET /api/metrics with pagination
    print("9. Testing /api/metrics with pagination")
    status, data = test_endpoint("/metrics", params={"page": 2, "per_page": 10})
    success = status == 200 and data and "pagination" in data
    page_info = data.get('pagination', {}) if data else {}
    details = f"Status: {status}, Page: {page_info.get('page')}, Per page: {page_info.get('per_page')}"
    print_test_result("GET /api/metrics?page=2&per_page=10", success, details)
    
    # Test 10: Error handling - Invalid outcome ID
    print("10. Testing error handling - Invalid outcome ID")
    status, data = test_endpoint("/metrics", params={"outcome": 999})
    success = status == 400 and data and "error" in data
    error_msg = data.get('error') if data else 'N/A'
    details = f"Status: {status}, Error: {error_msg}"
    print_test_result("GET /api/metrics?outcome=999 (invalid)", success, details)
    
    # Test 11: Error handling - Invalid type ID
    print("11. Testing error handling - Invalid type ID")
    status, data = test_endpoint("/metrics", params={"type": 999})
    success = status == 400 and data and "error" in data
    error_msg = data.get('error') if data else 'N/A'
    details = f"Status: {status}, Error: {error_msg}"
    print_test_result("GET /api/metrics?type=999 (invalid)", success, details)
    
    # Test 12: Error handling - Missing search query
    print("12. Testing error handling - Missing search query")
    status, data = test_endpoint("/metrics/search")
    success = status == 400 and data and "error" in data
    error_msg = data.get('error') if data else 'N/A'
    details = f"Status: {status}, Error: {error_msg}"
    print_test_result("GET /api/metrics/search (no query)", success, details)
    
    # Test 13: CORS headers check (basic)
    print("13. Testing CORS support")
    try:
        response = requests.options(f"{BASE_URL}/metrics")
        cors_headers = response.headers.get('Access-Control-Allow-Origin')
        success = cors_headers is not None
        details = f"CORS Origin header: {cors_headers or 'Not found'}"
        print_test_result("CORS preflight request", success, details)
    except Exception as e:
        print_test_result("CORS preflight request", False, f"Error: {e}")
    
    print("=" * 60)
    print("API ENDPOINT TESTING COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
