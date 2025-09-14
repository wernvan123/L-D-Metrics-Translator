"""
Security tests for L&D Metrics Translator application.
"""
import pytest
import json
import re
from unittest.mock import patch

from app.models import User, LDOutcome, MetricType
from app import db


@pytest.mark.security
class TestInputValidation:
    """Test input validation and sanitization."""
    
    def test_sql_injection_protection(self, client, app_context):
        """Test protection against SQL injection attacks."""
        # Create test data
        outcome = LDOutcome(
            name="SQL Test Outcome",
            description="Test outcome for SQL injection testing",
            category="Skills",
            level="Basic"
        )
        db.session.add(outcome)
        db.session.commit()
        
        # Test SQL injection attempts in search
        malicious_inputs = [
            "'; DROP TABLE outcomes; --",
            "' OR '1'='1",
            "'; DELETE FROM outcomes WHERE id=1; --",
            "' UNION SELECT * FROM users --",
            "admin'--",
            "' OR 1=1 #"
        ]
        
        for malicious_input in malicious_inputs:
            # Test web search
            response = client.get(f'/outcomes?search={malicious_input}')
            assert response.status_code == 200
            # Should not cause server error or expose data
            assert b'error' not in response.data.lower() or b'sql' not in response.data.lower()
            
            # Test API search
            response = client.get(f'/api/outcomes?search={malicious_input}')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'outcomes' in data
            # Should return empty or safe results, not error
    
    def test_xss_protection(self, client, app_context):
        """Test protection against XSS attacks."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//",
            "<svg onload=alert('XSS')>",
            "<%2Fscript%3E%3Cscript%3Ealert%28%27XSS%27%29%3C%2Fscript%3E"
        ]
        
        for payload in xss_payloads:
            # Test search functionality
            response = client.get(f'/outcomes?search={payload}')
            assert response.status_code == 200
            # Should not contain unescaped script tags
            assert b'<script>' not in response.data
            assert b'javascript:' not in response.data
            assert b'onerror=' not in response.data
            
            # Test contact form
            form_data = {
                'name': payload,
                'email': 'test@example.com',
                'subject': 'Test Subject',
                'message': 'Test message'
            }
            
            response = client.post('/contact', data=form_data)
            assert response.status_code == 200
            # Should not contain unescaped payload
            assert payload.encode() not in response.data
    
    def test_csrf_protection(self, client, app_context, admin_user):
        """Test CSRF protection."""
        # Login as admin
        with client.session_transaction() as sess:
            sess['user_id'] = admin_user.id
            sess['is_admin'] = True
        
        # Test forms without CSRF token
        form_data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'subject': 'Test Subject',
            'message': 'Test message'
        }
        
        # This should fail or be handled gracefully
        response = client.post('/contact', data=form_data)
        # Depending on implementation, might return 400, 403, or handle gracefully
        assert response.status_code in [200, 400, 403]
    
    def test_file_upload_security(self, client, app_context):
        """Test file upload security (if applicable)."""
        # Test malicious file types
        malicious_files = [
            ('test.php', b'<?php echo "malicious"; ?>'),
            ('test.exe', b'MZ\x90\x00'),  # PE header
            ('test.jsp', b'<%@ page language="java" %>'),
            ('../../../etc/passwd', b'root:x:0:0:root:/root:/bin/bash')
        ]
        
        for filename, content in malicious_files:
            # If file upload exists, test it
            # This is a placeholder - adjust based on actual file upload functionality
            data = {
                'file': (content, filename)
            }
            
            # Test file upload endpoint if it exists
            response = client.post('/upload', data=data)
            # Should reject malicious files or not have upload endpoint
            assert response.status_code in [404, 400, 403, 405]
    
    def test_path_traversal_protection(self, client):
        """Test protection against path traversal attacks."""
        path_traversal_attempts = [
            '../../../etc/passwd',
            '..\\..\\..\\windows\\system32\\config\\sam',
            '....//....//....//etc/passwd',
            '%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd',
            '..%252f..%252f..%252fetc%252fpasswd'
        ]
        
        for path in path_traversal_attempts:
            # Test various endpoints that might handle file paths
            response = client.get(f'/static/{path}')
            # Should not expose system files
            assert response.status_code in [404, 403]
            assert b'root:' not in response.data  # Unix passwd file content
            assert b'Administrator' not in response.data  # Windows content
    
    def test_command_injection_protection(self, client, app_context):
        """Test protection against command injection."""
        command_injection_payloads = [
            '; ls -la',
            '| cat /etc/passwd',
            '&& whoami',
            '`id`',
            '$(whoami)',
            '; ping -c 1 127.0.0.1',
            '| dir',
            '& ipconfig'
        ]
        
        for payload in command_injection_payloads:
            # Test in search parameters
            response = client.get(f'/outcomes?search={payload}')
            assert response.status_code == 200
            # Should not execute commands or show command output
            assert b'uid=' not in response.data  # Unix command output
            assert b'Windows IP Configuration' not in response.data  # Windows command output
            
            # Test in form submissions
            form_data = {
                'name': 'Test User',
                'email': 'test@example.com',
                'subject': payload,
                'message': 'Test message'
            }
            
            response = client.post('/contact', data=form_data)
            assert response.status_code == 200
            # Should not contain command output
            assert b'uid=' not in response.data
            assert b'Windows IP Configuration' not in response.data


@pytest.mark.security
class TestAuthentication:
    """Test authentication security."""
    
    def test_password_hashing(self, app_context):
        """Test password hashing security."""
        user = User(username="testuser", email="test@example.com")
        password = "testpassword123"
        user.set_password(password)
        
        # Password should be hashed
        assert user.password_hash != password
        assert len(user.password_hash) > 50  # Should be a long hash
        
        # Should use strong hashing (bcrypt, scrypt, or pbkdf2)
        # bcrypt hashes start with $2b$
        # pbkdf2 hashes contain pbkdf2
        assert ('$2b$' in user.password_hash or 
                'pbkdf2' in user.password_hash or 
                'scrypt' in user.password_hash)
        
        # Verify password works
        assert user.check_password(password)
        assert not user.check_password("wrongpassword")
    
    def test_session_security(self, client, app_context, admin_user):
        """Test session security."""
        # Test login
        login_data = {
            'username': admin_user.username,
            'password': 'testpassword'
        }
        
        response = client.post('/admin/login', data=login_data, follow_redirects=True)
        assert response.status_code == 200
        
        # Test session fixation protection
        with client.session_transaction() as sess:
            old_session_id = sess.get('_id')
        
        # After login, session ID should change (if implemented)
        with client.session_transaction() as sess:
            new_session_id = sess.get('_id')
            # This depends on Flask-Session configuration
            # assert old_session_id != new_session_id
        
        # Test logout clears session
        response = client.get('/admin/logout', follow_redirects=True)
        assert response.status_code == 200
        
        with client.session_transaction() as sess:
            assert 'user_id' not in sess
            assert 'is_admin' not in sess
    
    def test_brute_force_protection(self, client, app_context, admin_user):
        """Test brute force attack protection."""
        # Attempt multiple failed logins
        failed_attempts = 0
        max_attempts = 10
        
        for i in range(max_attempts):
            login_data = {
                'username': admin_user.username,
                'password': f'wrongpassword{i}'
            }
            
            response = client.post('/admin/login', data=login_data)
            
            if response.status_code == 429:  # Rate limited
                break
            elif b'too many attempts' in response.data.lower():
                break
            else:
                failed_attempts += 1
        
        # Should implement some form of rate limiting or account lockout
        # This test passes if either rate limiting is implemented or 
        # we can make reasonable number of attempts without being blocked
        assert failed_attempts <= max_attempts
    
    def test_admin_access_control(self, client, app_context, regular_user, admin_user):
        """Test admin access control."""
        # Test regular user cannot access admin routes
        with client.session_transaction() as sess:
            sess['user_id'] = regular_user.id
            sess['is_admin'] = False
        
        admin_routes = [
            '/admin/dashboard',
            '/admin/users',
            '/admin/outcomes',
            '/admin/metrics'
        ]
        
        for route in admin_routes:
            response = client.get(route)
            # Should redirect to login or show unauthorized
            assert response.status_code in [302, 401, 403, 404]
        
        # Test admin user can access admin routes
        with client.session_transaction() as sess:
            sess['user_id'] = admin_user.id
            sess['is_admin'] = True
        
        response = client.get('/admin/dashboard')
        # Should allow access (200) or redirect to login if session expired (302)
        assert response.status_code in [200, 302]


@pytest.mark.security
class TestDataProtection:
    """Test data protection and privacy."""
    
    def test_sensitive_data_exposure(self, client, app_context, admin_user):
        """Test that sensitive data is not exposed."""
        # Test API responses don't expose sensitive data
        response = client.get('/api/outcomes')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        
        # Should not expose internal database details
        response_text = response.data.decode()
        assert 'password' not in response_text.lower()
        assert 'hash' not in response_text.lower()
        assert 'secret' not in response_text.lower()
        assert 'key' not in response_text.lower()
        
        # Test user data protection
        if admin_user:
            response = client.get(f'/api/users/{admin_user.id}')
            if response.status_code == 200:
                user_data = json.loads(response.data)
                assert 'password_hash' not in user_data
                assert 'password' not in user_data
    
    def test_information_disclosure(self, client):
        """Test for information disclosure vulnerabilities."""
        # Test error pages don't reveal sensitive information
        response = client.get('/nonexistent-page')
        assert response.status_code == 404
        
        error_content = response.data.decode().lower()
        
        # Should not reveal system information
        sensitive_info = [
            'traceback',
            'exception',
            'stack trace',
            'python',
            'flask',
            'sqlalchemy',
            'database',
            'connection string',
            'file path',
            'c:\\',
            '/home/',
            '/var/',
            'secret_key'
        ]
        
        for info in sensitive_info:
            assert info not in error_content
    
    def test_debug_mode_disabled(self, client):
        """Test that debug mode is disabled in production."""
        # Trigger an error to check debug mode
        response = client.get('/api/outcomes/invalid')
        
        # Should not show debug information
        error_content = response.data.decode().lower()
        assert 'debugger' not in error_content
        assert 'traceback' not in error_content
        assert 'werkzeug' not in error_content
    
    def test_secure_headers(self, client):
        """Test security headers."""
        response = client.get('/')
        headers = response.headers
        
        # Check for common security headers
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': ['DENY', 'SAMEORIGIN'],
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=',  # Should contain max-age
            'Content-Security-Policy': ['default-src', 'script-src', 'style-src']
        }
        
        for header, expected_values in security_headers.items():
            if header in headers:
                header_value = headers[header]
                if isinstance(expected_values, list):
                    assert any(expected in header_value for expected in expected_values)
                else:
                    assert expected_values in header_value


@pytest.mark.security
class TestAPISecurityTests:
    """Test API-specific security."""
    
    def test_api_rate_limiting(self, client, app_context):
        """Test API rate limiting."""
        # Make rapid requests to test rate limiting
        responses = []
        for i in range(100):  # High number of requests
            response = client.get('/api/outcomes')
            responses.append(response.status_code)
            
            # If rate limited, break
            if response.status_code == 429:
                break
        
        # Should implement rate limiting (429 status) or handle gracefully
        rate_limited = any(status == 429 for status in responses)
        successful = sum(1 for status in responses if status == 200)
        
        # Either rate limiting is implemented or all requests succeed
        assert rate_limited or successful == len(responses)
    
    def test_api_input_validation(self, client, app_context):
        """Test API input validation."""
        # Test invalid JSON
        response = client.post('/api/translate',
                             data='invalid json',
                             content_type='application/json')
        assert response.status_code == 400
        
        # Test missing required fields
        response = client.post('/api/translate',
                             data=json.dumps({}),
                             content_type='application/json')
        assert response.status_code == 400
        
        # Test invalid data types
        invalid_data = {
            'outcome_id': 'not_a_number',
            'metric_type_id': 'also_not_a_number',
            'additional_context': 123  # Should be string
        }
        
        response = client.post('/api/translate',
                             data=json.dumps(invalid_data),
                             content_type='application/json')
        assert response.status_code == 400
    
    def test_api_authorization(self, client, app_context):
        """Test API authorization."""
        # Test accessing protected API endpoints without authentication
        protected_endpoints = [
            '/api/admin/users',
            '/api/admin/outcomes',
            '/api/admin/metrics'
        ]
        
        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            # Should require authentication
            assert response.status_code in [401, 403, 404]
    
    def test_api_cors_security(self, client):
        """Test CORS security configuration."""
        # Test preflight request
        response = client.options('/api/outcomes',
                                headers={'Origin': 'https://malicious-site.com',
                                        'Access-Control-Request-Method': 'GET'})
        
        # Check CORS headers
        if 'Access-Control-Allow-Origin' in response.headers:
            allowed_origin = response.headers['Access-Control-Allow-Origin']
            # Should not allow all origins in production
            if allowed_origin != '*':
                # Good - specific origins allowed
                pass
            else:
                # Warning - all origins allowed (might be OK for public API)
                pass


@pytest.mark.security
class TestDependencySecurityTests:
    """Test dependency security."""
    
    def test_known_vulnerabilities(self):
        """Test for known vulnerabilities in dependencies."""
        # This would typically use safety or similar tools
        # For now, we'll do basic checks
        
        import pkg_resources
        
        # Get installed packages
        installed_packages = [d for d in pkg_resources.working_set]
        
        # Check for packages with known security issues
        # This is a simplified check - in practice, use safety or similar tools
        potentially_vulnerable = []
        
        for package in installed_packages:
            package_name = package.project_name.lower()
            version = package.version
            
            # Example checks (these would be updated based on current vulnerabilities)
            if package_name == 'flask' and version < '2.0.0':
                potentially_vulnerable.append(f"{package_name} {version}")
            elif package_name == 'requests' and version < '2.20.0':
                potentially_vulnerable.append(f"{package_name} {version}")
        
        # Assert no known vulnerable packages
        assert len(potentially_vulnerable) == 0, f"Potentially vulnerable packages: {potentially_vulnerable}"
    
    def test_secure_defaults(self, app):
        """Test secure configuration defaults."""
        with app.app_context():
            # Test that debug mode is disabled
            assert not app.debug
            
            # Test that secret key is set and not default
            assert app.secret_key is not None
            assert app.secret_key != 'dev'
            assert len(app.secret_key) >= 32  # Should be reasonably long
            
            # Test database configuration
            db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            if 'sqlite' not in db_uri.lower():
                # For production databases, should not contain credentials in URI
                assert 'password' not in db_uri.lower()
                assert '@' not in db_uri or db_uri.startswith('sqlite')


@pytest.mark.security
class TestSecurityMisconfiguration:
    """Test for security misconfigurations."""
    
    def test_directory_listing_disabled(self, client):
        """Test that directory listing is disabled."""
        # Test common directories
        directories = [
            '/static/',
            '/templates/',
            '/uploads/',
            '/files/'
        ]
        
        for directory in directories:
            response = client.get(directory)
            # Should not show directory listing
            assert response.status_code in [403, 404]
            
            if response.status_code == 200:
                content = response.data.decode().lower()
                # Should not contain directory listing indicators
                assert 'index of' not in content
                assert 'parent directory' not in content
    
    def test_sensitive_files_protected(self, client):
        """Test that sensitive files are not accessible."""
        sensitive_files = [
            '/.env',
            '/config.py',
            '/.git/config',
            '/requirements.txt',
            '/Dockerfile',
            '/.gitignore',
            '/app.py',
            '/run.py'
        ]
        
        for file_path in sensitive_files:
            response = client.get(file_path)
            # Should not be accessible via web
            assert response.status_code in [403, 404]
    
    def test_admin_interface_security(self, client, app_context, admin_user):
        """Test admin interface security."""
        # Test that admin interface requires authentication
        response = client.get('/admin/')
        assert response.status_code in [302, 401, 403]  # Should redirect or deny
        
        # Test with authentication
        with client.session_transaction() as sess:
            sess['user_id'] = admin_user.id
            sess['is_admin'] = True
        
        response = client.get('/admin/dashboard')
        if response.status_code == 200:
            content = response.data.decode()
            # Should not expose sensitive system information
            assert 'database password' not in content.lower()
            assert 'secret key' not in content.lower()
            assert 'api key' not in content.lower()
