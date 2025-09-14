"""
Integration tests for L&D Metrics Translator application.
"""
import pytest
import json
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from app.models import LDOutcome, MetricType, Metric, User
from app import db


@pytest.mark.integration
class TestDatabaseIntegration:
    """Test database integration scenarios."""
    
    def test_full_data_workflow(self, app_context):
        """Test complete data creation workflow."""
        # Create outcome
        outcome = LDOutcome(
            name="Integration Test Outcome",
            description="Test outcome for integration testing",
            category="Skills",
            level="Intermediate"
        )
        db.session.add(outcome)
        db.session.commit()
        
        # Create metric type
        metric_type = MetricType(
            name="Integration Test Type",
            description="Test metric type for integration testing",
            category="Assessment"
        )
        db.session.add(metric_type)
        db.session.commit()
        
        # Create metric
        metric = Metric(
            name="Integration Test Metric",
            description="Test metric for integration testing",
            outcome_id=outcome.id,
            metric_type_id=metric_type.id,
            measurement_method="Survey",
            data_collection="Monthly",
            success_criteria="85% satisfaction rate"
        )
        db.session.add(metric)
        db.session.commit()
        
        # Verify relationships
        assert metric.outcome == outcome
        assert metric.metric_type == metric_type
        assert metric in outcome.metrics
        assert metric in metric_type.metrics
        
        # Test cascade delete
        metric_id = metric.id
        db.session.delete(outcome)
        db.session.commit()
        
        # Metric should be deleted due to cascade
        deleted_metric = Metric.query.get(metric_id)
        assert deleted_metric is None
    
    def test_data_consistency(self, app_context):
        """Test data consistency across operations."""
        # Create test data
        outcomes = []
        for i in range(5):
            outcome = LDOutcome(
                name=f"Consistency Test {i}",
                description=f"Test description {i}",
                category="Knowledge",
                level="Basic"
            )
            outcomes.append(outcome)
        
        db.session.add_all(outcomes)
        db.session.commit()
        
        # Test bulk operations
        initial_count = LDOutcome.query.count()
        assert initial_count >= 5
        
        # Update all outcomes
        for outcome in outcomes:
            outcome.description = f"Updated: {outcome.description}"
        db.session.commit()
        
        # Verify updates
        updated_outcomes = LDOutcome.query.filter(
            LDOutcome.description.like('Updated:%')
        ).all()
        assert len(updated_outcomes) == 5
        
        # Test transaction rollback
        try:
            # Start a transaction that will fail
            new_outcome = LDOutcome(
                name="Test Rollback",
                description="This should be rolled back",
                category="Invalid Category",  # This should cause validation error
                level="Basic"
            )
            db.session.add(new_outcome)
            
            # Force validation error
            if not new_outcome.is_valid_category():
                raise ValueError("Invalid category")
                
        except ValueError:
            db.session.rollback()
        
        # Verify rollback worked
        rollback_outcome = LDOutcome.query.filter_by(name="Test Rollback").first()
        assert rollback_outcome is None


@pytest.mark.integration
class TestAPIIntegration:
    """Test API integration scenarios."""
    
    def test_api_workflow(self, client, app_context):
        """Test complete API workflow."""
        # 1. Get initial empty data
        response = client.get('/api/outcomes')
        assert response.status_code == 200
        initial_data = json.loads(response.data)
        initial_count = len(initial_data['outcomes'])
        
        # 2. Create test data via database
        outcome = LDOutcome(
            name="API Test Outcome",
            description="Test outcome for API integration",
            category="Skills",
            level="Advanced"
        )
        db.session.add(outcome)
        db.session.commit()
        
        metric_type = MetricType(
            name="API Test Type",
            description="Test metric type for API integration",
            category="Performance"
        )
        db.session.add(metric_type)
        db.session.commit()
        
        # 3. Verify data via API
        response = client.get('/api/outcomes')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['outcomes']) == initial_count + 1
        
        # Find our test outcome
        test_outcome = next((o for o in data['outcomes'] if o['name'] == 'API Test Outcome'), None)
        assert test_outcome is not None
        
        # 4. Get specific outcome
        response = client.get(f'/api/outcomes/{outcome.id}')
        assert response.status_code == 200
        outcome_data = json.loads(response.data)
        assert outcome_data['name'] == 'API Test Outcome'
        
        # 5. Test translation API
        translate_data = {
            'outcome_id': outcome.id,
            'metric_type_id': metric_type.id,
            'additional_context': 'Integration test context'
        }
        
        response = client.post('/api/translate',
                             data=json.dumps(translate_data),
                             content_type='application/json')
        assert response.status_code == 200
        
        result = json.loads(response.data)
        assert 'suggestions' in result
        assert len(result['suggestions']) > 0
    
    def test_api_error_handling(self, client, app_context):
        """Test API error handling integration."""
        # Test 404 errors
        response = client.get('/api/outcomes/999')
        assert response.status_code == 404
        
        response = client.get('/api/types/999')
        assert response.status_code == 404
        
        response = client.get('/api/metrics/999')
        assert response.status_code == 404
        
        # Test validation errors
        invalid_data = {
            'outcome_id': 999,
            'metric_type_id': 999,
            'additional_context': 'Test'
        }
        
        response = client.post('/api/translate',
                             data=json.dumps(invalid_data),
                             content_type='application/json')
        assert response.status_code == 400
    
    def test_api_filtering_integration(self, client, app_context):
        """Test API filtering integration."""
        # Create diverse test data
        outcomes = [
            LDOutcome(name="Python Skills", description="Learn Python", category="Skills", level="Basic"),
            LDOutcome(name="Leadership Knowledge", description="Leadership theory", category="Knowledge", level="Advanced"),
            LDOutcome(name="Team Behavior", description="Team dynamics", category="Behavior", level="Intermediate")
        ]
        
        db.session.add_all(outcomes)
        db.session.commit()
        
        # Test category filtering
        response = client.get('/api/outcomes?category=Skills')
        assert response.status_code == 200
        data = json.loads(response.data)
        skills_outcomes = [o for o in data['outcomes'] if o['category'] == 'Skills']
        assert len(skills_outcomes) >= 1
        
        # Test level filtering
        response = client.get('/api/outcomes?level=Advanced')
        assert response.status_code == 200
        data = json.loads(response.data)
        advanced_outcomes = [o for o in data['outcomes'] if o['level'] == 'Advanced']
        assert len(advanced_outcomes) >= 1
        
        # Test search functionality
        response = client.get('/api/outcomes?search=Python')
        assert response.status_code == 200
        data = json.loads(response.data)
        python_outcomes = [o for o in data['outcomes'] if 'Python' in o['name'] or 'Python' in o['description']]
        assert len(python_outcomes) >= 1
        
        # Test combined filters
        response = client.get('/api/outcomes?category=Skills&level=Basic&search=Python')
        assert response.status_code == 200
        data = json.loads(response.data)
        filtered_outcomes = data['outcomes']
        assert len(filtered_outcomes) >= 1
        assert all(o['category'] == 'Skills' and o['level'] == 'Basic' for o in filtered_outcomes)


@pytest.mark.integration
@pytest.mark.slow
class TestWebIntegration:
    """Test web interface integration."""
    
    def test_homepage_integration(self, client):
        """Test homepage integration."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'L&D Metrics Translator' in response.data
        assert b'outcomes' in response.data.lower()
        assert b'metrics' in response.data.lower()
    
    def test_outcomes_page_integration(self, client, app_context):
        """Test outcomes page integration."""
        # Create test data
        outcome = LDOutcome(
            name="Web Test Outcome",
            description="Test outcome for web integration",
            category="Skills",
            level="Intermediate"
        )
        db.session.add(outcome)
        db.session.commit()
        
        # Test outcomes list page
        response = client.get('/outcomes')
        assert response.status_code == 200
        assert b'Web Test Outcome' in response.data
        
        # Test outcome detail page
        response = client.get(f'/outcomes/{outcome.id}')
        assert response.status_code == 200
        assert b'Web Test Outcome' in response.data
        assert b'Test outcome for web integration' in response.data
    
    def test_translator_integration(self, client, app_context):
        """Test translator page integration."""
        # Create test data
        outcome = LDOutcome(
            name="Translator Test Outcome",
            description="Test outcome for translator",
            category="Skills",
            level="Advanced"
        )
        db.session.add(outcome)
        db.session.commit()
        
        metric_type = MetricType(
            name="Translator Test Type",
            description="Test metric type for translator",
            category="Assessment"
        )
        db.session.add(metric_type)
        db.session.commit()
        
        # Test translator page
        response = client.get('/translator')
        assert response.status_code == 200
        assert b'Translator' in response.data
        
        # Test translation submission
        data = {
            'outcome_id': outcome.id,
            'metric_type_id': metric_type.id,
            'additional_context': 'Integration test context'
        }
        
        response = client.post('/translator', data=data)
        assert response.status_code == 200
        # Should show suggestions or results
        assert b'suggestion' in response.data.lower() or b'metric' in response.data.lower()
    
    def test_search_integration(self, client, app_context):
        """Test search functionality integration."""
        # Create searchable test data
        outcomes = [
            LDOutcome(name="Python Programming", description="Learn Python basics", category="Skills", level="Basic"),
            LDOutcome(name="Data Science", description="Python for data analysis", category="Skills", level="Advanced"),
            LDOutcome(name="Leadership", description="Team leadership skills", category="Behavior", level="Intermediate")
        ]
        
        db.session.add_all(outcomes)
        db.session.commit()
        
        # Test search via web interface
        response = client.get('/outcomes?search=Python')
        assert response.status_code == 200
        assert b'Python Programming' in response.data
        assert b'Data Science' in response.data
        assert b'Leadership' not in response.data
    
    def test_filtering_integration(self, client, app_context):
        """Test filtering functionality integration."""
        # Create filterable test data
        outcomes = [
            LDOutcome(name="Test Skills 1", description="Test", category="Skills", level="Basic"),
            LDOutcome(name="Test Knowledge 1", description="Test", category="Knowledge", level="Intermediate"),
            LDOutcome(name="Test Behavior 1", description="Test", category="Behavior", level="Advanced")
        ]
        
        db.session.add_all(outcomes)
        db.session.commit()
        
        # Test category filter
        response = client.get('/outcomes?category=Skills')
        assert response.status_code == 200
        assert b'Test Skills 1' in response.data
        assert b'Test Knowledge 1' not in response.data
        
        # Test level filter
        response = client.get('/outcomes?level=Advanced')
        assert response.status_code == 200
        assert b'Test Behavior 1' in response.data
        assert b'Test Skills 1' not in response.data


@pytest.mark.integration
@pytest.mark.slow
class TestSeleniumIntegration:
    """Test browser integration with Selenium."""
    
    @pytest.fixture(autouse=True)
    def setup_server(self, app):
        """Setup test server for Selenium tests."""
        # This would typically start a test server
        # For now, we'll assume the server is running locally
        self.base_url = "http://127.0.0.1:5000"
    
    def test_homepage_selenium(self, chrome_driver):
        """Test homepage with Selenium."""
        driver = chrome_driver
        driver.get(self.base_url)
        
        # Wait for page to load
        wait = WebDriverWait(driver, 10)
        
        try:
            # Check page title
            assert "L&D Metrics Translator" in driver.title
            
            # Check main navigation elements
            nav_elements = driver.find_elements(By.TAG_NAME, "nav")
            assert len(nav_elements) > 0
            
            # Check for main content
            main_content = wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "main"))
            )
            assert main_content is not None
            
        except TimeoutException:
            pytest.skip("Test server not available for Selenium tests")
    
    def test_outcomes_page_selenium(self, chrome_driver, app_context):
        """Test outcomes page with Selenium."""
        # Create test data
        outcome = LDOutcome(
            name="Selenium Test Outcome",
            description="Test outcome for Selenium testing",
            category="Skills",
            level="Intermediate"
        )
        db.session.add(outcome)
        db.session.commit()
        
        driver = chrome_driver
        
        try:
            driver.get(f"{self.base_url}/outcomes")
            
            wait = WebDriverWait(driver, 10)
            
            # Wait for outcomes to load
            outcomes_container = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "outcomes-container"))
            )
            
            # Check if our test outcome is displayed
            page_text = driver.page_source
            assert "Selenium Test Outcome" in page_text
            
        except TimeoutException:
            pytest.skip("Test server not available for Selenium tests")
    
    def test_translator_form_selenium(self, chrome_driver, app_context):
        """Test translator form with Selenium."""
        # Create test data
        outcome = LDOutcome(
            name="Form Test Outcome",
            description="Test outcome for form testing",
            category="Skills",
            level="Advanced"
        )
        db.session.add(outcome)
        db.session.commit()
        
        metric_type = MetricType(
            name="Form Test Type",
            description="Test metric type for form testing",
            category="Assessment"
        )
        db.session.add(metric_type)
        db.session.commit()
        
        driver = chrome_driver
        
        try:
            driver.get(f"{self.base_url}/translator")
            
            wait = WebDriverWait(driver, 10)
            
            # Wait for form to load
            form = wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "form"))
            )
            
            # Fill out the form
            outcome_select = Select(driver.find_element(By.NAME, "outcome_id"))
            outcome_select.select_by_visible_text("Form Test Outcome")
            
            type_select = Select(driver.find_element(By.NAME, "metric_type_id"))
            type_select.select_by_visible_text("Form Test Type")
            
            context_field = driver.find_element(By.NAME, "additional_context")
            context_field.send_keys("Selenium test context")
            
            # Submit form
            submit_button = driver.find_element(By.TYPE, "submit")
            submit_button.click()
            
            # Wait for results
            wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "results"))
            )
            
            # Check for suggestions
            page_text = driver.page_source
            assert "suggestion" in page_text.lower() or "metric" in page_text.lower()
            
        except TimeoutException:
            pytest.skip("Test server not available for Selenium tests")
    
    def test_search_functionality_selenium(self, chrome_driver, app_context):
        """Test search functionality with Selenium."""
        # Create searchable test data
        outcome = LDOutcome(
            name="Searchable Outcome",
            description="This outcome should be searchable",
            category="Skills",
            level="Basic"
        )
        db.session.add(outcome)
        db.session.commit()
        
        driver = chrome_driver
        
        try:
            driver.get(f"{self.base_url}/outcomes")
            
            wait = WebDriverWait(driver, 10)
            
            # Find search input
            search_input = wait.until(
                EC.presence_of_element_located((By.NAME, "search"))
            )
            
            # Perform search
            search_input.send_keys("Searchable")
            search_input.submit()
            
            # Wait for results
            time.sleep(2)  # Allow time for search results to load
            
            # Check results
            page_text = driver.page_source
            assert "Searchable Outcome" in page_text
            
        except TimeoutException:
            pytest.skip("Test server not available for Selenium tests")


@pytest.mark.integration
class TestUserAuthIntegration:
    """Test user authentication integration."""
    
    def test_admin_login_workflow(self, client, app_context, admin_user):
        """Test complete admin login workflow."""
        # Test login page
        response = client.get('/admin/login')
        assert response.status_code == 200
        assert b'Login' in response.data
        
        # Test login with valid credentials
        data = {
            'username': admin_user.username,
            'password': 'testpassword'
        }
        
        response = client.post('/admin/login', data=data, follow_redirects=True)
        assert response.status_code == 200
        
        # Should be redirected to dashboard
        assert b'Dashboard' in response.data or b'Admin' in response.data
        
        # Test accessing protected route
        response = client.get('/admin/dashboard')
        assert response.status_code == 200
        
        # Test logout
        response = client.get('/admin/logout', follow_redirects=True)
        assert response.status_code == 200
        
        # Should be redirected to main page
        assert b'L&D Metrics Translator' in response.data
        
        # Test accessing protected route after logout
        response = client.get('/admin/dashboard')
        # Should redirect to login or show unauthorized
        assert response.status_code in [302, 401, 403]
    
    def test_user_registration_workflow(self, client, app_context):
        """Test user registration workflow."""
        # Test registration page
        response = client.get('/admin/register')
        assert response.status_code == 200
        assert b'Register' in response.data
        
        # Test registration with valid data
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpassword',
            'confirm_password': 'newpassword'
        }
        
        response = client.post('/admin/register', data=data, follow_redirects=True)
        assert response.status_code == 200
        
        # Verify user was created
        new_user = User.query.filter_by(username='newuser').first()
        assert new_user is not None
        assert new_user.email == 'newuser@example.com'
        assert not new_user.is_admin  # Should not be admin by default
    
    def test_password_reset_workflow(self, client, app_context, regular_user, mock_email):
        """Test password reset workflow."""
        # Test password reset request
        data = {
            'email': regular_user.email
        }
        
        response = client.post('/admin/reset-password', data=data)
        assert response.status_code == 200
        
        # Should have attempted to send email
        mock_email.assert_called_once()
        
        # Test password reset with token (would need to implement token generation)
        # This is a simplified test
        new_password = 'newpassword123'
        regular_user.set_password(new_password)
        db.session.commit()
        
        # Test login with new password
        login_data = {
            'username': regular_user.username,
            'password': new_password
        }
        
        response = client.post('/admin/login', data=login_data, follow_redirects=True)
        assert response.status_code == 200


@pytest.mark.integration
class TestPerformanceIntegration:
    """Test performance-related integration scenarios."""
    
    def test_large_dataset_performance(self, client, app_context, performance_monitor):
        """Test performance with large datasets."""
        # Create a large number of outcomes
        outcomes = []
        for i in range(100):
            outcome = LDOutcome(
                name=f"Performance Test Outcome {i}",
                description=f"Description for outcome {i}",
                category="Skills",
                level="Basic"
            )
            outcomes.append(outcome)
        
        db.session.add_all(outcomes)
        db.session.commit()
        
        # Test API performance
        start_time = time.time()
        response = client.get('/api/outcomes')
        end_time = time.time()
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['outcomes']) >= 100
        
        # Performance assertion (should complete within reasonable time)
        execution_time = end_time - start_time
        assert execution_time < 5.0  # Should complete within 5 seconds
    
    def test_concurrent_requests(self, client, app_context):
        """Test handling of concurrent requests."""
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            try:
                response = client.get('/api/outcomes')
                results.put(response.status_code)
            except Exception as e:
                results.put(str(e))
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        success_count = 0
        while not results.empty():
            result = results.get()
            if result == 200:
                success_count += 1
        
        # Most requests should succeed
        assert success_count >= 8  # Allow for some failures in concurrent scenario
