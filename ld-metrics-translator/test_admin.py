#!/usr/bin/env python3
"""
Test script for the admin interface functionality.
This script tests all admin routes and functionality.
"""

import os
import sys
import requests
import json
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import AdminUser, Metric, LDOutcome, MetricType, AuditLog


class AdminTester:
    """Test class for admin functionality."""
    
    def __init__(self, base_url='http://localhost:5000'):
        self.base_url = base_url
        self.session = requests.Session()
        self.csrf_token = None
    
    def test_admin_login(self, username='admin', password='admin123'):
        """Test admin login functionality."""
        print(f"Testing admin login with {username}...")
        
        # Get login page and extract CSRF token
        response = self.session.get(f'{self.base_url}/admin/login')
        if response.status_code != 200:
            print(f"❌ Failed to access login page: {response.status_code}")
            return False
        
        # Extract CSRF token (simplified - in real implementation you'd parse HTML)
        # For now, we'll skip CSRF token extraction in this test
        
        # Attempt login
        login_data = {
            'username': username,
            'password': password
        }
        
        response = self.session.post(f'{self.base_url}/admin/login', data=login_data)
        
        if response.status_code == 200 and 'dashboard' in response.url:
            print("[PASS] Admin login successful")
            return True
        else:
            print(f"[FAIL] Admin login failed: {response.status_code}")
            return False
    
    def test_admin_dashboard(self):
        """Test admin dashboard access."""
        print("Testing admin dashboard...")
        
        response = self.session.get(f'{self.base_url}/admin/dashboard')
        if response.status_code == 200:
            print("[PASS] Admin dashboard accessible")
            return True
        else:
            print(f"[FAIL] Admin dashboard failed: {response.status_code}")
            return False
    
    def test_metrics_management(self):
        """Test metrics CRUD operations."""
        print("Testing metrics management...")
        
        # Test metrics list
        response = self.session.get(f'{self.base_url}/admin/metrics')
        if response.status_code == 200:
            print("[PASS] Metrics list accessible")
        else:
            print(f"[FAIL] Metrics list failed: {response.status_code}")
            return False
        
        # Test add metric form
        response = self.session.get(f'{self.base_url}/admin/metrics/add')
        if response.status_code == 200:
            print("[PASS] Add metric form accessible")
        else:
            print(f"[FAIL] Add metric form failed: {response.status_code}")
            return False
        
        return True
    
    def test_bulk_import(self):
        """Test bulk import functionality."""
        print("Testing bulk import...")
        
        response = self.session.get(f'{self.base_url}/admin/import')
        if response.status_code == 200:
            print("[PASS] Bulk import page accessible")
            return True
        else:
            print(f"[FAIL] Bulk import failed: {response.status_code}")
            return False
    
    def test_user_management(self):
        """Test admin user management."""
        print("Testing user management...")
        
        response = self.session.get(f'{self.base_url}/admin/users')
        if response.status_code == 200:
            print("[PASS] User management accessible")
            return True
        else:
            print(f"[FAIL] User management failed: {response.status_code}")
            return False
    
    def test_audit_logs(self):
        """Test audit logs functionality."""
        print("Testing audit logs...")
        
        response = self.session.get(f'{self.base_url}/admin/audit')
        if response.status_code == 200:
            print("[PASS] Audit logs accessible")
            return True
        else:
            print(f"[FAIL] Audit logs failed: {response.status_code}")
            return False
    
    def run_all_tests(self):
        """Run all admin tests."""
        print("=" * 50)
        print("L&D Metrics Translator - Admin Interface Tests")
        print("=" * 50)
        
        tests = [
            self.test_admin_login,
            self.test_admin_dashboard,
            self.test_metrics_management,
            self.test_bulk_import,
            self.test_user_management,
            self.test_audit_logs
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            try:
                if test():
                    passed += 1
            except Exception as e:
                print(f"[FAIL] Test failed with exception: {e}")
        
        print("\n" + "=" * 50)
        print(f"Test Results: {passed}/{total} tests passed")
        print("=" * 50)
        
        return passed == total


def test_database_models():
    """Test admin database models."""
    print("Testing admin database models...")
    
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        
        try:
            # Test AdminUser model
            admin = AdminUser(
                username='testadmin',
                email='test@example.com',
                is_active=True
            )
            admin.set_password('testpass123')
            db.session.add(admin)
            db.session.commit()
            
            # Test password verification
            assert admin.check_password('testpass123'), "Password verification failed"
            assert not admin.check_password('wrongpass'), "Password verification should fail"
            
            # Test AuditLog model
            log = AuditLog(
                admin_user_id=admin.id,
                action='TEST_ACTION',
                details='Test audit log entry',
                ip_address='127.0.0.1'
            )
            db.session.add(log)
            db.session.commit()
            
            # Verify relationships
            assert admin.audit_logs.count() == 1, "Audit log relationship failed"
            assert log.admin_user.username == 'testadmin', "Admin user relationship failed"
            
            print("[PASS] Database models test passed")
            return True
            
        except Exception as e:
            print(f"[FAIL] Database models test failed: {e}")
            return False
        finally:
            db.session.rollback()


def main():
    """Main test function."""
    if len(sys.argv) > 1 and sys.argv[1] == '--models-only':
        # Test only database models
        test_database_models()
        return
    
    # Test database models first
    if not test_database_models():
        print("Database model tests failed. Aborting web tests.")
        return
    
    # Test web interface (requires running server)
    print("\nNote: Web interface tests require the server to be running.")
    print("Start the server with: python run.py")
    
    choice = input("Is the server running? (y/n): ").lower()
    if choice == 'y':
        tester = AdminTester()
        tester.run_all_tests()
    else:
        print("Skipping web interface tests.")
        print("To test the web interface:")
        print("1. Run: python run.py")
        print("2. Run: python test_admin.py")


if __name__ == '__main__':
    main()
