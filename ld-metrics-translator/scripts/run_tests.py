#!/usr/bin/env python3
"""
Comprehensive test runner for L&D Metrics Translator application.
This script runs all types of tests and generates reports.
"""
import os
import sys
import subprocess
import argparse
import time
from pathlib import Path


class TestRunner:
    """Main test runner class."""
    
    def __init__(self, project_root=None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.results = {}
        
    def run_command(self, command, description, timeout=300):
        """Run a command and capture results."""
        print(f"\n{'='*60}")
        print(f"Running: {description}")
        print(f"Command: {' '.join(command)}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            self.results[description] = {
                'success': result.returncode == 0,
                'duration': duration,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
            
            print(f"Duration: {duration:.2f} seconds")
            print(f"Return code: {result.returncode}")
            
            if result.stdout:
                print(f"\nSTDOUT:\n{result.stdout}")
            
            if result.stderr:
                print(f"\nSTDERR:\n{result.stderr}")
                
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            print(f"Command timed out after {timeout} seconds")
            self.results[description] = {
                'success': False,
                'duration': timeout,
                'error': 'Timeout',
                'returncode': -1
            }
            return False
        except Exception as e:
            print(f"Error running command: {e}")
            self.results[description] = {
                'success': False,
                'duration': 0,
                'error': str(e),
                'returncode': -1
            }
            return False
    
    def run_unit_tests(self):
        """Run unit tests."""
        return self.run_command(
            ['python', '-m', 'pytest', 'tests/', '-m', 'unit', '-v'],
            'Unit Tests'
        )
    
    def run_integration_tests(self):
        """Run integration tests."""
        return self.run_command(
            ['python', '-m', 'pytest', 'tests/', '-m', 'integration', '-v'],
            'Integration Tests',
            timeout=600  # Longer timeout for integration tests
        )
    
    def run_api_tests(self):
        """Run API tests."""
        return self.run_command(
            ['python', '-m', 'pytest', 'tests/', '-m', 'api', '-v'],
            'API Tests'
        )
    
    def run_performance_tests(self):
        """Run performance tests."""
        return self.run_command(
            ['python', '-m', 'pytest', 'tests/', '-m', 'performance', '-v', '--tb=short'],
            'Performance Tests',
            timeout=900  # Longer timeout for performance tests
        )
    
    def run_security_tests(self):
        """Run security tests."""
        return self.run_command(
            ['python', '-m', 'pytest', 'tests/', '-m', 'security', '-v'],
            'Security Tests'
        )
    
    def run_accessibility_tests(self):
        """Run accessibility tests."""
        return self.run_command(
            ['python', '-m', 'pytest', 'tests/', '-m', 'accessibility', '-v', '--tb=short'],
            'Accessibility Tests',
            timeout=600
        )
    
    def run_coverage_tests(self):
        """Run tests with coverage reporting."""
        return self.run_command(
            ['python', '-m', 'pytest', 'tests/', '--cov=app', '--cov-report=html', '--cov-report=term'],
            'Coverage Tests'
        )
    
    def run_linting(self):
        """Run code linting."""
        success = True
        
        # Flake8
        if not self.run_command(['flake8', 'app/', 'tests/'], 'Flake8 Linting'):
            success = False
        
        # Black (check only)
        if not self.run_command(['black', '--check', 'app/', 'tests/'], 'Black Code Formatting Check'):
            success = False
        
        # isort (check only)
        if not self.run_command(['isort', '--check-only', 'app/', 'tests/'], 'Import Sorting Check'):
            success = False
        
        return success
    
    def run_type_checking(self):
        """Run type checking with mypy."""
        return self.run_command(['mypy', 'app/'], 'Type Checking (MyPy)')
    
    def run_security_scan(self):
        """Run security vulnerability scanning."""
        success = True
        
        # Bandit security scan
        if not self.run_command(['bandit', '-r', 'app/', '-f', 'json', '-o', 'bandit-report.json'], 'Bandit Security Scan'):
            success = False
        
        # Safety check for known vulnerabilities
        if not self.run_command(['safety', 'check', '--json', '--output', 'safety-report.json'], 'Safety Vulnerability Check'):
            success = False
        
        return success
    
    def generate_report(self):
        """Generate comprehensive test report."""
        report_path = self.project_root / 'test-report.html'
        
        html_content = self._generate_html_report()
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\nTest report generated: {report_path}")
        return report_path
    
    def _generate_html_report(self):
        """Generate HTML test report."""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r['success'])
        failed_tests = total_tests - passed_tests
        
        total_duration = sum(r['duration'] for r in self.results.values())
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>L&D Metrics Translator - Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .metric {{ background: #ecf0f1; padding: 15px; border-radius: 5px; flex: 1; text-align: center; }}
        .metric.success {{ background: #d5f4e6; }}
        .metric.failure {{ background: #fadbd8; }}
        .test-result {{ margin: 10px 0; padding: 15px; border-radius: 5px; }}
        .test-result.success {{ background: #d5f4e6; border-left: 5px solid #27ae60; }}
        .test-result.failure {{ background: #fadbd8; border-left: 5px solid #e74c3c; }}
        .test-details {{ margin-top: 10px; font-family: monospace; font-size: 12px; }}
        .collapsible {{ cursor: pointer; }}
        .content {{ display: none; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>L&D Metrics Translator - Test Report</h1>
        <p>Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="summary">
        <div class="metric">
            <h3>Total Tests</h3>
            <div style="font-size: 24px; font-weight: bold;">{total_tests}</div>
        </div>
        <div class="metric success">
            <h3>Passed</h3>
            <div style="font-size: 24px; font-weight: bold;">{passed_tests}</div>
        </div>
        <div class="metric failure">
            <h3>Failed</h3>
            <div style="font-size: 24px; font-weight: bold;">{failed_tests}</div>
        </div>
        <div class="metric">
            <h3>Total Duration</h3>
            <div style="font-size: 24px; font-weight: bold;">{total_duration:.1f}s</div>
        </div>
    </div>
    
    <h2>Test Results</h2>
"""
        
        for test_name, result in self.results.items():
            status_class = 'success' if result['success'] else 'failure'
            status_text = 'PASSED' if result['success'] else 'FAILED'
            
            html += f"""
    <div class="test-result {status_class}">
        <div class="collapsible" onclick="toggleContent('{test_name.replace(' ', '_')}')">
            <strong>{test_name}</strong> - {status_text} ({result['duration']:.2f}s)
        </div>
        <div id="{test_name.replace(' ', '_')}" class="content">
            <div class="test-details">
                <strong>Return Code:</strong> {result.get('returncode', 'N/A')}<br>
"""
            
            if 'stdout' in result and result['stdout']:
                html += f"<strong>Output:</strong><br><pre>{result['stdout'][:1000]}{'...' if len(result['stdout']) > 1000 else ''}</pre>"
            
            if 'stderr' in result and result['stderr']:
                html += f"<strong>Errors:</strong><br><pre>{result['stderr'][:1000]}{'...' if len(result['stderr']) > 1000 else ''}</pre>"
            
            if 'error' in result:
                html += f"<strong>Error:</strong> {result['error']}<br>"
            
            html += """
            </div>
        </div>
    </div>
"""
        
        html += """
    <script>
        function toggleContent(id) {
            var content = document.getElementById(id);
            content.style.display = content.style.display === 'block' ? 'none' : 'block';
        }
    </script>
</body>
</html>
"""
        return html


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Run comprehensive tests for L&D Metrics Translator')
    parser.add_argument('--unit', action='store_true', help='Run unit tests only')
    parser.add_argument('--integration', action='store_true', help='Run integration tests only')
    parser.add_argument('--api', action='store_true', help='Run API tests only')
    parser.add_argument('--performance', action='store_true', help='Run performance tests only')
    parser.add_argument('--security', action='store_true', help='Run security tests only')
    parser.add_argument('--accessibility', action='store_true', help='Run accessibility tests only')
    parser.add_argument('--coverage', action='store_true', help='Run coverage tests only')
    parser.add_argument('--lint', action='store_true', help='Run linting only')
    parser.add_argument('--type-check', action='store_true', help='Run type checking only')
    parser.add_argument('--security-scan', action='store_true', help='Run security scanning only')
    parser.add_argument('--all', action='store_true', help='Run all tests (default)')
    parser.add_argument('--quick', action='store_true', help='Run quick tests only (unit, api, lint)')
    parser.add_argument('--no-report', action='store_true', help='Skip generating HTML report')
    
    args = parser.parse_args()
    
    # If no specific test type is specified, run all
    if not any([args.unit, args.integration, args.api, args.performance, 
                args.security, args.accessibility, args.coverage, args.lint, 
                args.type_check, args.security_scan, args.quick]):
        args.all = True
    
    runner = TestRunner()
    
    print("Starting L&D Metrics Translator Test Suite")
    print(f"Project root: {runner.project_root}")
    
    # Quick test suite
    if args.quick:
        print("\nRunning Quick Test Suite...")
        runner.run_unit_tests()
        runner.run_api_tests()
        runner.run_linting()
    
    # Individual test types
    elif args.unit:
        runner.run_unit_tests()
    elif args.integration:
        runner.run_integration_tests()
    elif args.api:
        runner.run_api_tests()
    elif args.performance:
        runner.run_performance_tests()
    elif args.security:
        runner.run_security_tests()
    elif args.accessibility:
        runner.run_accessibility_tests()
    elif args.coverage:
        runner.run_coverage_tests()
    elif args.lint:
        runner.run_linting()
    elif args.type_check:
        runner.run_type_checking()
    elif args.security_scan:
        runner.run_security_scan()
    
    # Full test suite
    elif args.all:
        print("\nRunning Full Test Suite...")
        
        # Code quality checks
        print("\n" + "="*60)
        print("PHASE 1: CODE QUALITY CHECKS")
        print("="*60)
        runner.run_linting()
        runner.run_type_checking()
        
        # Unit and API tests
        print("\n" + "="*60)
        print("PHASE 2: UNIT AND API TESTS")
        print("="*60)
        runner.run_unit_tests()
        runner.run_api_tests()
        
        # Integration tests
        print("\n" + "="*60)
        print("PHASE 3: INTEGRATION TESTS")
        print("="*60)
        runner.run_integration_tests()
        
        # Security tests
        print("\n" + "="*60)
        print("PHASE 4: SECURITY TESTS")
        print("="*60)
        runner.run_security_tests()
        runner.run_security_scan()
        
        # Performance tests
        print("\n" + "="*60)
        print("PHASE 5: PERFORMANCE TESTS")
        print("="*60)
        runner.run_performance_tests()
        
        # Accessibility tests
        print("\n" + "="*60)
        print("PHASE 6: ACCESSIBILITY TESTS")
        print("="*60)
        runner.run_accessibility_tests()
        
        # Coverage report
        print("\n" + "="*60)
        print("PHASE 7: COVERAGE ANALYSIS")
        print("="*60)
        runner.run_coverage_tests()
    
    # Generate report
    if not args.no_report:
        report_path = runner.generate_report()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    total_tests = len(runner.results)
    passed_tests = sum(1 for r in runner.results.values() if r['success'])
    failed_tests = total_tests - passed_tests
    
    print(f"Total test suites: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    
    if failed_tests > 0:
        print("\nFailed test suites:")
        for test_name, result in runner.results.items():
            if not result['success']:
                print(f"  - {test_name}")
    
    # Exit with appropriate code
    sys.exit(0 if failed_tests == 0 else 1)


if __name__ == '__main__':
    main()
