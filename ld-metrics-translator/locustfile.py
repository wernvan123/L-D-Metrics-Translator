"""
Locust performance testing configuration for L&D Metrics Translator.
Usage: locust -f locustfile.py --host=http://127.0.0.1:5000
"""
from locust import HttpUser, task, between
import json
import random


class LDMetricsUser(HttpUser):
    """Simulated user for L&D Metrics Translator application."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Called when a user starts."""
        # Get initial data for realistic testing
        self.outcomes = []
        self.metric_types = []
        
        # Fetch available outcomes
        response = self.client.get("/api/outcomes")
        if response.status_code == 200:
            data = response.json()
            self.outcomes = data.get('outcomes', [])
        
        # Fetch available metric types
        response = self.client.get("/api/types")
        if response.status_code == 200:
            data = response.json()
            self.metric_types = data.get('metric_types', [])
    
    @task(3)
    def view_homepage(self):
        """Visit the homepage."""
        self.client.get("/")
    
    @task(5)
    def browse_outcomes(self):
        """Browse outcomes page."""
        self.client.get("/outcomes")
    
    @task(4)
    def browse_metrics(self):
        """Browse metrics page."""
        self.client.get("/metrics")
    
    @task(3)
    def browse_metric_types(self):
        """Browse metric types page."""
        self.client.get("/types")
    
    @task(2)
    def view_translator(self):
        """View translator page."""
        self.client.get("/translator")
    
    @task(6)
    def api_get_outcomes(self):
        """API: Get outcomes."""
        self.client.get("/api/outcomes")
    
    @task(4)
    def api_get_metrics(self):
        """API: Get metrics."""
        self.client.get("/api/metrics")
    
    @task(3)
    def api_get_metric_types(self):
        """API: Get metric types."""
        self.client.get("/api/types")
    
    @task(2)
    def api_search_outcomes(self):
        """API: Search outcomes."""
        search_terms = ["skills", "knowledge", "behavior", "learning", "development"]
        search_term = random.choice(search_terms)
        self.client.get(f"/api/outcomes?search={search_term}")
    
    @task(2)
    def api_filter_outcomes(self):
        """API: Filter outcomes by category."""
        categories = ["Skills", "Knowledge", "Behavior"]
        category = random.choice(categories)
        self.client.get(f"/api/outcomes?category={category}")
    
    @task(1)
    def api_filter_outcomes_by_level(self):
        """API: Filter outcomes by level."""
        levels = ["Basic", "Intermediate", "Advanced"]
        level = random.choice(levels)
        self.client.get(f"/api/outcomes?level={level}")
    
    @task(2)
    def view_outcome_detail(self):
        """View individual outcome detail."""
        if self.outcomes:
            outcome = random.choice(self.outcomes)
            outcome_id = outcome.get('id')
            if outcome_id:
                self.client.get(f"/outcomes/{outcome_id}")
    
    @task(1)
    def api_get_outcome_detail(self):
        """API: Get individual outcome detail."""
        if self.outcomes:
            outcome = random.choice(self.outcomes)
            outcome_id = outcome.get('id')
            if outcome_id:
                self.client.get(f"/api/outcomes/{outcome_id}")
    
    @task(1)
    def use_translator(self):
        """Use the translator functionality."""
        if self.outcomes and self.metric_types:
            outcome = random.choice(self.outcomes)
            metric_type = random.choice(self.metric_types)
            
            # Web form submission
            data = {
                'outcome_id': outcome.get('id'),
                'metric_type_id': metric_type.get('id'),
                'additional_context': 'Performance testing context for translation'
            }
            
            self.client.post("/translator", data=data)
    
    @task(1)
    def api_translate(self):
        """API: Use translation endpoint."""
        if self.outcomes and self.metric_types:
            outcome = random.choice(self.outcomes)
            metric_type = random.choice(self.metric_types)
            
            data = {
                'outcome_id': outcome.get('id'),
                'metric_type_id': metric_type.get('id'),
                'additional_context': 'API performance testing context'
            }
            
            self.client.post("/api/translate", 
                           data=json.dumps(data),
                           headers={'Content-Type': 'application/json'})
    
    @task(1)
    def search_outcomes_web(self):
        """Search outcomes via web interface."""
        search_terms = ["python", "leadership", "data", "communication", "management"]
        search_term = random.choice(search_terms)
        self.client.get(f"/outcomes?search={search_term}")
    
    @task(1)
    def filter_outcomes_web(self):
        """Filter outcomes via web interface."""
        categories = ["Skills", "Knowledge", "Behavior"]
        levels = ["Basic", "Intermediate", "Advanced"]
        
        category = random.choice(categories)
        level = random.choice(levels)
        
        self.client.get(f"/outcomes?category={category}&level={level}")
    
    @task(1)
    def view_about_page(self):
        """View about page."""
        self.client.get("/about")
    
    @task(1)
    def view_help_page(self):
        """View help page."""
        self.client.get("/help")
    
    @task(1)
    def contact_form_submission(self):
        """Submit contact form."""
        data = {
            'name': 'Performance Test User',
            'email': 'performance@test.com',
            'subject': 'Performance Testing',
            'message': 'This is a performance test message from Locust'
        }
        
        self.client.post("/contact", data=data)


class AdminUser(HttpUser):
    """Simulated admin user for testing admin functionality."""
    
    wait_time = between(2, 5)
    weight = 1  # Lower weight means fewer admin users
    
    def on_start(self):
        """Login as admin user."""
        # Attempt admin login
        login_data = {
            'username': 'admin',
            'password': 'admin123'  # Use test admin credentials
        }
        
        response = self.client.post("/admin/login", data=login_data)
        if response.status_code == 200:
            self.logged_in = True
        else:
            self.logged_in = False
    
    @task(2)
    def admin_dashboard(self):
        """Visit admin dashboard."""
        if self.logged_in:
            self.client.get("/admin/dashboard")
    
    @task(1)
    def admin_outcomes(self):
        """Visit admin outcomes page."""
        if self.logged_in:
            self.client.get("/admin/outcomes")
    
    @task(1)
    def admin_metrics(self):
        """Visit admin metrics page."""
        if self.logged_in:
            self.client.get("/admin/metrics")
    
    @task(1)
    def admin_users(self):
        """Visit admin users page."""
        if self.logged_in:
            self.client.get("/admin/users")


class APIOnlyUser(HttpUser):
    """User that only uses API endpoints."""
    
    wait_time = between(0.5, 2)
    weight = 2  # More API-only users
    
    @task(10)
    def api_outcomes(self):
        """Get outcomes via API."""
        self.client.get("/api/outcomes")
    
    @task(8)
    def api_metrics(self):
        """Get metrics via API."""
        self.client.get("/api/metrics")
    
    @task(6)
    def api_types(self):
        """Get metric types via API."""
        self.client.get("/api/types")
    
    @task(4)
    def api_search(self):
        """Search via API."""
        search_terms = ["skill", "knowledge", "behavior", "learning"]
        search_term = random.choice(search_terms)
        self.client.get(f"/api/outcomes?search={search_term}")
    
    @task(3)
    def api_filter(self):
        """Filter via API."""
        categories = ["Skills", "Knowledge", "Behavior"]
        category = random.choice(categories)
        self.client.get(f"/api/outcomes?category={category}")
    
    @task(2)
    def api_pagination(self):
        """Test API pagination."""
        page = random.randint(1, 3)
        per_page = random.choice([10, 20, 50])
        self.client.get(f"/api/outcomes?page={page}&per_page={per_page}")


class MobileUser(HttpUser):
    """Simulated mobile user with different usage patterns."""
    
    wait_time = between(2, 6)  # Mobile users typically slower
    weight = 3
    
    def on_start(self):
        """Set mobile user agent."""
        self.client.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15'
        })
    
    @task(5)
    def mobile_homepage(self):
        """Visit homepage on mobile."""
        self.client.get("/")
    
    @task(4)
    def mobile_outcomes(self):
        """Browse outcomes on mobile."""
        self.client.get("/outcomes")
    
    @task(3)
    def mobile_search(self):
        """Search on mobile."""
        search_terms = ["skills", "training", "development"]
        search_term = random.choice(search_terms)
        self.client.get(f"/outcomes?search={search_term}")
    
    @task(2)
    def mobile_translator(self):
        """Use translator on mobile."""
        self.client.get("/translator")
    
    @task(1)
    def mobile_help(self):
        """View help on mobile."""
        self.client.get("/help")


# Custom load test scenarios
class StressTestUser(HttpUser):
    """High-intensity user for stress testing."""
    
    wait_time = between(0.1, 0.5)  # Very fast requests
    weight = 0  # Only used in specific stress test scenarios
    
    @task
    def rapid_api_calls(self):
        """Make rapid API calls."""
        endpoints = ["/api/outcomes", "/api/metrics", "/api/types"]
        endpoint = random.choice(endpoints)
        self.client.get(endpoint)


# Performance test configuration
class PerformanceTestConfig:
    """Configuration for different performance test scenarios."""
    
    @staticmethod
    def light_load():
        """Light load test configuration."""
        return {
            'users': 10,
            'spawn_rate': 2,
            'run_time': '5m'
        }
    
    @staticmethod
    def normal_load():
        """Normal load test configuration."""
        return {
            'users': 50,
            'spawn_rate': 5,
            'run_time': '10m'
        }
    
    @staticmethod
    def heavy_load():
        """Heavy load test configuration."""
        return {
            'users': 100,
            'spawn_rate': 10,
            'run_time': '15m'
        }
    
    @staticmethod
    def stress_test():
        """Stress test configuration."""
        return {
            'users': 200,
            'spawn_rate': 20,
            'run_time': '20m'
        }


# Example usage commands:
"""
# Light load test
locust -f locustfile.py --host=http://127.0.0.1:5000 -u 10 -r 2 -t 5m

# Normal load test  
locust -f locustfile.py --host=http://127.0.0.1:5000 -u 50 -r 5 -t 10m

# Heavy load test
locust -f locustfile.py --host=http://127.0.0.1:5000 -u 100 -r 10 -t 15m

# Stress test
locust -f locustfile.py --host=http://127.0.0.1:5000 -u 200 -r 20 -t 20m

# API-only test
locust -f locustfile.py --host=http://127.0.0.1:5000 -u 30 -r 5 -t 10m APIOnlyUser

# Web UI (default)
locust -f locustfile.py --host=http://127.0.0.1:5000
"""
