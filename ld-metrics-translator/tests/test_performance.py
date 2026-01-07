"""
Performance tests for L&D Metrics Translator application.
"""
import pytest
import time
import json
import threading

try:
    import psutil  # pragma: no cover - optional dependency
    PSUTIL_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    psutil = None
    PSUTIL_AVAILABLE = False

try:
    from memory_profiler import profile  # pragma: no cover - optional dependency
except ImportError:  # pragma: no cover - optional dependency
    def profile(func):
        return func

pytestmark = pytest.mark.skipif(not PSUTIL_AVAILABLE, reason="psutil not installed")
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.models import LDOutcome, MetricType, Metric
from app import db


@pytest.mark.performance
@pytest.mark.slow
class TestDatabasePerformance:
    """Test database performance."""
    
    def test_bulk_insert_performance(self, app_context, performance_monitor):
        """Test bulk insert performance."""
        start_time = time.time()
        
        # Create large number of outcomes
        outcomes = []
        for i in range(1000):
            outcome = LDOutcome(
                name=f"Performance Test Outcome {i}",
                description=f"Description for performance test outcome {i}",
                category="Skills",
                level="Basic"
            )
            outcomes.append(outcome)
        
        # Bulk insert
        db.session.add_all(outcomes)
        db.session.commit()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Performance assertions
        assert execution_time < 10.0  # Should complete within 10 seconds
        assert len(outcomes) == 1000
        
        # Verify data integrity
        count = LDOutcome.query.count()
        assert count >= 1000
    
    def test_query_performance(self, app_context, performance_monitor):
        """Test query performance with large dataset."""
        # Create test data
        outcomes = []
        for i in range(500):
            outcome = LDOutcome(
                name=f"Query Test Outcome {i}",
                description=f"Description {i} with searchable content",
                category="Skills" if i % 2 == 0 else "Knowledge",
                level="Basic" if i % 3 == 0 else "Intermediate"
            )
            outcomes.append(outcome)
        
        db.session.add_all(outcomes)
        db.session.commit()
        
        # Test different query patterns
        queries = [
            lambda: LDOutcome.query.all(),
            lambda: LDOutcome.query.filter_by(category="Skills").all(),
            lambda: LDOutcome.query.filter_by(level="Basic").all(),
            lambda: LDOutcome.search("searchable"),
            lambda: LDOutcome.query.filter(LDOutcome.name.like('%Test%')).all()
        ]
        
        for query_func in queries:
            start_time = time.time()
            results = query_func()
            end_time = time.time()
            
            execution_time = end_time - start_time
            assert execution_time < 2.0  # Each query should complete within 2 seconds
            assert len(results) > 0
    
    def test_relationship_query_performance(self, app_context, performance_monitor):
        """Test performance of relationship queries."""
        # Create test data with relationships
        outcome = LDOutcome(
            name="Relationship Test Outcome",
            description="Test outcome for relationship performance",
            category="Skills",
            level="Advanced"
        )
        db.session.add(outcome)
        db.session.commit()
        
        metric_type = MetricType(
            name="Relationship Test Type",
            description="Test metric type for relationship performance",
            category="Assessment"
        )
        db.session.add(metric_type)
        db.session.commit()
        
        # Create many metrics
        metrics = []
        for i in range(100):
            metric = Metric(
                name=f"Relationship Test Metric {i}",
                description=f"Description {i}",
                outcome_id=outcome.id,
                metric_type_id=metric_type.id,
                measurement_method="Survey",
                data_collection="Monthly",
                success_criteria="80%"
            )
            metrics.append(metric)
        
        db.session.add_all(metrics)
        db.session.commit()
        
        # Test relationship queries
        start_time = time.time()
        outcome_metrics = outcome.metrics
        end_time = time.time()
        
        execution_time = end_time - start_time
        assert execution_time < 1.0  # Should complete within 1 second
        assert len(outcome_metrics) == 100
        
        # Test reverse relationship
        start_time = time.time()
        type_metrics = metric_type.metrics
        end_time = time.time()
        
        execution_time = end_time - start_time
        assert execution_time < 1.0  # Should complete within 1 second
        assert len(type_metrics) == 100
    
    def test_concurrent_database_access(self, app_context, performance_monitor):
        """Test concurrent database access performance."""
        def create_outcome(thread_id):
            outcome = LDOutcome(
                name=f"Concurrent Test Outcome {thread_id}",
                description=f"Description for thread {thread_id}",
                category="Skills",
                level="Basic"
            )
            db.session.add(outcome)
            db.session.commit()
            return outcome.id
        
        def query_outcomes():
            return LDOutcome.query.limit(10).all()
        
        start_time = time.time()
        
        # Use ThreadPoolExecutor for concurrent operations
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit create tasks
            create_futures = [executor.submit(create_outcome, i) for i in range(10)]
            
            # Submit query tasks
            query_futures = [executor.submit(query_outcomes) for _ in range(5)]
            
            # Wait for all tasks to complete
            create_results = [future.result() for future in as_completed(create_futures)]
            query_results = [future.result() for future in as_completed(query_futures)]
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Performance assertions
        assert execution_time < 15.0  # Should complete within 15 seconds
        assert len(create_results) == 10
        assert len(query_results) == 5
        assert all(isinstance(result, int) for result in create_results)
        assert all(isinstance(result, list) for result in query_results)


@pytest.mark.performance
@pytest.mark.slow
class TestAPIPerformance:
    """Test API performance."""
    
    def test_api_response_time(self, client, app_context, performance_monitor):
        """Test API response times."""
        # Create test data
        outcomes = []
        for i in range(100):
            outcome = LDOutcome(
                name=f"API Performance Test {i}",
                description=f"Description {i}",
                category="Skills",
                level="Basic"
            )
            outcomes.append(outcome)
        
        db.session.add_all(outcomes)
        db.session.commit()
        
        # Test different API endpoints
        endpoints = [
            '/api/outcomes',
            '/api/types',
            '/api/metrics',
            '/api/outcomes?category=Skills',
            '/api/outcomes?search=Performance'
        ]
        
        for endpoint in endpoints:
            start_time = time.time()
            response = client.get(endpoint)
            end_time = time.time()
            
            execution_time = end_time - start_time
            
            assert response.status_code == 200
            assert execution_time < 2.0  # Should respond within 2 seconds
            
            # Verify response is valid JSON
            data = json.loads(response.data)
            assert isinstance(data, dict)
    
    def test_api_concurrent_requests(self, client, app_context, performance_monitor):
        """Test API performance under concurrent load."""
        # Create test data
        outcomes = []
        for i in range(50):
            outcome = LDOutcome(
                name=f"Concurrent API Test {i}",
                description=f"Description {i}",
                category="Skills",
                level="Basic"
            )
            outcomes.append(outcome)
        
        db.session.add_all(outcomes)
        db.session.commit()
        
        def make_api_request(endpoint):
            start_time = time.time()
            response = client.get(endpoint)
            end_time = time.time()
            return {
                'status_code': response.status_code,
                'response_time': end_time - start_time,
                'endpoint': endpoint
            }
        
        # Test concurrent requests
        endpoints = ['/api/outcomes', '/api/types', '/api/metrics'] * 10  # 30 total requests
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_api_request, endpoint) for endpoint in endpoints]
            results = [future.result() for future in as_completed(futures)]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Performance assertions
        assert total_time < 30.0  # All requests should complete within 30 seconds
        assert len(results) == 30
        
        # Check individual response times
        successful_requests = [r for r in results if r['status_code'] == 200]
        assert len(successful_requests) >= 25  # At least 25 should succeed
        
        avg_response_time = sum(r['response_time'] for r in successful_requests) / len(successful_requests)
        assert avg_response_time < 3.0  # Average response time should be under 3 seconds
    
    def test_api_pagination_performance(self, client, app_context, performance_monitor):
        """Test API pagination performance."""
        # Create large dataset
        outcomes = []
        for i in range(200):
            outcome = LDOutcome(
                name=f"Pagination Test {i}",
                description=f"Description {i}",
                category="Skills",
                level="Basic"
            )
            outcomes.append(outcome)
        
        db.session.add_all(outcomes)
        db.session.commit()
        
        # Test different page sizes
        page_sizes = [10, 20, 50, 100]
        
        for page_size in page_sizes:
            start_time = time.time()
            response = client.get(f'/api/outcomes?page=1&per_page={page_size}')
            end_time = time.time()
            
            execution_time = end_time - start_time
            
            assert response.status_code == 200
            assert execution_time < 3.0  # Should respond within 3 seconds
            
            data = json.loads(response.data)
            assert len(data['outcomes']) <= page_size
    
    def test_translation_api_performance(self, client, app_context, performance_monitor):
        """Test translation API performance."""
        # Create test data
        outcome = LDOutcome(
            name="Translation Performance Test",
            description="Test outcome for translation performance",
            category="Skills",
            level="Advanced"
        )
        db.session.add(outcome)
        db.session.commit()
        
        metric_type = MetricType(
            name="Translation Performance Type",
            description="Test metric type for translation performance",
            category="Assessment"
        )
        db.session.add(metric_type)
        db.session.commit()
        
        # Test translation requests
        translate_data = {
            'outcome_id': outcome.id,
            'metric_type_id': metric_type.id,
            'additional_context': 'Performance test context with detailed information about the learning scenario'
        }
        
        # Single request performance
        start_time = time.time()
        response = client.post('/api/translate',
                             data=json.dumps(translate_data),
                             content_type='application/json')
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        assert response.status_code == 200
        assert execution_time < 5.0  # Translation should complete within 5 seconds
        
        data = json.loads(response.data)
        assert 'suggestions' in data
        assert len(data['suggestions']) > 0
        
        # Multiple concurrent translation requests
        def make_translation_request():
            start_time = time.time()
            response = client.post('/api/translate',
                                 data=json.dumps(translate_data),
                                 content_type='application/json')
            end_time = time.time()
            return {
                'status_code': response.status_code,
                'response_time': end_time - start_time
            }
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(make_translation_request) for _ in range(5)]
            results = [future.result() for future in as_completed(futures)]
        
        # Check concurrent performance
        successful_requests = [r for r in results if r['status_code'] == 200]
        assert len(successful_requests) >= 4  # At least 4 should succeed
        
        avg_response_time = sum(r['response_time'] for r in successful_requests) / len(successful_requests)
        assert avg_response_time < 10.0  # Average should be under 10 seconds for concurrent requests


@pytest.mark.performance
class TestMemoryPerformance:
    """Test memory usage performance."""
    
    def test_memory_usage_large_dataset(self, app_context, performance_monitor):
        """Test memory usage with large datasets."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Create large dataset
        outcomes = []
        for i in range(1000):
            outcome = LDOutcome(
                name=f"Memory Test Outcome {i}",
                description=f"Long description for memory test outcome {i} " * 10,  # Make it longer
                category="Skills",
                level="Basic"
            )
            outcomes.append(outcome)
        
        db.session.add_all(outcomes)
        db.session.commit()
        
        # Query all data
        all_outcomes = LDOutcome.query.all()
        
        current_memory = process.memory_info().rss
        memory_increase = current_memory - initial_memory
        
        # Memory assertions (in bytes)
        assert memory_increase < 100 * 1024 * 1024  # Should not increase by more than 100MB
        assert len(all_outcomes) == 1000
        
        # Clean up
        del all_outcomes
        del outcomes
    
    @profile
    def test_memory_profile_api_requests(self, client, app_context):
        """Test memory profile of API requests."""
        # Create test data
        outcomes = []
        for i in range(100):
            outcome = LDOutcome(
                name=f"Memory Profile Test {i}",
                description=f"Description {i}",
                category="Skills",
                level="Basic"
            )
            outcomes.append(outcome)
        
        db.session.add_all(outcomes)
        db.session.commit()
        
        # Make multiple API requests
        for _ in range(10):
            response = client.get('/api/outcomes')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert len(data['outcomes']) >= 100
    
    def test_memory_leak_detection(self, client, app_context):
        """Test for memory leaks in repeated operations."""
        process = psutil.Process()
        
        # Create initial test data
        outcome = LDOutcome(
            name="Memory Leak Test",
            description="Test outcome for memory leak detection",
            category="Skills",
            level="Basic"
        )
        db.session.add(outcome)
        db.session.commit()
        
        # Record initial memory
        initial_memory = process.memory_info().rss
        
        # Perform repeated operations
        for i in range(100):
            # API request
            response = client.get('/api/outcomes')
            assert response.status_code == 200
            
            # Database query
            outcomes = LDOutcome.query.all()
            assert len(outcomes) >= 1
            
            # Create and delete temporary data
            temp_outcome = LDOutcome(
                name=f"Temp {i}",
                description="Temporary",
                category="Skills",
                level="Basic"
            )
            db.session.add(temp_outcome)
            db.session.commit()
            
            db.session.delete(temp_outcome)
            db.session.commit()
        
        # Check final memory
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory leak assertion (should not increase significantly)
        assert memory_increase < 50 * 1024 * 1024  # Should not increase by more than 50MB


@pytest.mark.performance
class TestFrontendPerformance:
    """Test frontend performance metrics."""
    
    def test_page_load_performance(self, client, performance_monitor):
        """Test page load performance."""
        pages = [
            '/',
            '/outcomes',
            '/types',
            '/metrics',
            '/translator',
            '/about',
            '/help'
        ]
        
        for page in pages:
            start_time = time.time()
            response = client.get(page)
            end_time = time.time()
            
            execution_time = end_time - start_time
            
            assert response.status_code == 200
            assert execution_time < 3.0  # Page should load within 3 seconds
            
            # Check response size (should not be too large)
            content_length = len(response.data)
            assert content_length < 1024 * 1024  # Should be less than 1MB
    
    def test_static_asset_performance(self, client):
        """Test static asset loading performance."""
        static_assets = [
            '/static/css/style.css',
            '/static/js/main.js',
            '/static/js/translator.js'
        ]
        
        for asset in static_assets:
            start_time = time.time()
            response = client.get(asset)
            end_time = time.time()
            
            execution_time = end_time - start_time
            
            # Assets should exist and load quickly
            if response.status_code == 200:
                assert execution_time < 1.0  # Should load within 1 second
                
                # Check asset size
                content_length = len(response.data)
                assert content_length < 500 * 1024  # Should be less than 500KB
    
    def test_form_submission_performance(self, client, app_context, performance_monitor):
        """Test form submission performance."""
        # Create test data
        outcome = LDOutcome(
            name="Form Performance Test",
            description="Test outcome for form performance",
            category="Skills",
            level="Advanced"
        )
        db.session.add(outcome)
        db.session.commit()
        
        metric_type = MetricType(
            name="Form Performance Type",
            description="Test metric type for form performance",
            category="Assessment"
        )
        db.session.add(metric_type)
        db.session.commit()
        
        # Test translator form submission
        form_data = {
            'outcome_id': outcome.id,
            'metric_type_id': metric_type.id,
            'additional_context': 'Performance test context'
        }
        
        start_time = time.time()
        response = client.post('/translator', data=form_data)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        assert response.status_code == 200
        assert execution_time < 5.0  # Form submission should complete within 5 seconds
        
        # Test contact form submission
        contact_data = {
            'name': 'Performance Test User',
            'email': 'performance@test.com',
            'subject': 'Performance Test',
            'message': 'This is a performance test message'
        }
        
        start_time = time.time()
        response = client.post('/contact', data=contact_data)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        assert response.status_code == 200
        assert execution_time < 3.0  # Contact form should complete within 3 seconds


@pytest.mark.performance
class TestLoadTesting:
    """Test application under load."""
    
    def test_sustained_load(self, client, app_context, performance_monitor):
        """Test application under sustained load."""
        # Create test data
        outcomes = []
        for i in range(50):
            outcome = LDOutcome(
                name=f"Load Test Outcome {i}",
                description=f"Description {i}",
                category="Skills",
                level="Basic"
            )
            outcomes.append(outcome)
        
        db.session.add_all(outcomes)
        db.session.commit()
        
        # Define load test scenarios
        def api_load_test():
            endpoints = ['/api/outcomes', '/api/types', '/api/metrics']
            results = []
            
            for _ in range(20):  # 20 requests per thread
                endpoint = endpoints[len(results) % len(endpoints)]
                start_time = time.time()
                response = client.get(endpoint)
                end_time = time.time()
                
                results.append({
                    'status_code': response.status_code,
                    'response_time': end_time - start_time,
                    'endpoint': endpoint
                })
                
                time.sleep(0.1)  # Small delay between requests
            
            return results
        
        def web_load_test():
            pages = ['/', '/outcomes', '/metrics', '/translator']
            results = []
            
            for _ in range(15):  # 15 requests per thread
                page = pages[len(results) % len(pages)]
                start_time = time.time()
                response = client.get(page)
                end_time = time.time()
                
                results.append({
                    'status_code': response.status_code,
                    'response_time': end_time - start_time,
                    'page': page
                })
                
                time.sleep(0.15)  # Small delay between requests
            
            return results
        
        # Run load test with multiple threads
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit API load tests
            api_futures = [executor.submit(api_load_test) for _ in range(3)]
            
            # Submit web load tests
            web_futures = [executor.submit(web_load_test) for _ in range(2)]
            
            # Collect results
            api_results = []
            for future in as_completed(api_futures):
                api_results.extend(future.result())
            
            web_results = []
            for future in as_completed(web_futures):
                web_results.extend(future.result())
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Performance assertions
        assert total_time < 60.0  # Should complete within 60 seconds
        
        # Check API results
        successful_api = [r for r in api_results if r['status_code'] == 200]
        assert len(successful_api) >= len(api_results) * 0.9  # 90% success rate
        
        avg_api_time = sum(r['response_time'] for r in successful_api) / len(successful_api)
        assert avg_api_time < 2.0  # Average API response time under 2 seconds
        
        # Check web results
        successful_web = [r for r in web_results if r['status_code'] == 200]
        assert len(successful_web) >= len(web_results) * 0.9  # 90% success rate
        
        avg_web_time = sum(r['response_time'] for r in successful_web) / len(successful_web)
        assert avg_web_time < 3.0  # Average web response time under 3 seconds
    
    def test_stress_testing(self, client, app_context, performance_monitor):
        """Test application under stress conditions."""
        # Create minimal test data
        outcome = LDOutcome(
            name="Stress Test Outcome",
            description="Test outcome for stress testing",
            category="Skills",
            level="Basic"
        )
        db.session.add(outcome)
        db.session.commit()
        
        def stress_worker():
            results = []
            for _ in range(50):  # High number of requests per worker
                try:
                    start_time = time.time()
                    response = client.get('/api/outcomes')
                    end_time = time.time()
                    
                    results.append({
                        'success': response.status_code == 200,
                        'response_time': end_time - start_time
                    })
                except Exception as e:
                    results.append({
                        'success': False,
                        'error': str(e)
                    })
            
            return results
        
        # Run stress test with high concurrency
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:  # High concurrency
            futures = [executor.submit(stress_worker) for _ in range(8)]
            all_results = []
            
            for future in as_completed(futures):
                all_results.extend(future.result())
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Stress test assertions
        successful_requests = [r for r in all_results if r.get('success', False)]
        success_rate = len(successful_requests) / len(all_results)
        
        # Under stress, we expect some degradation but not complete failure
        assert success_rate >= 0.7  # At least 70% success rate under stress
        assert total_time < 120.0  # Should complete within 2 minutes
        
        if successful_requests:
            avg_response_time = sum(r['response_time'] for r in successful_requests) / len(successful_requests)
            assert avg_response_time < 10.0  # Average response time under stress should be under 10 seconds
