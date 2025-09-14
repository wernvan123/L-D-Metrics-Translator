# L&D Metrics Translator - Testing Documentation

This document provides comprehensive information about the testing infrastructure for the L&D Metrics Translator application.

## Table of Contents

1. [Overview](#overview)
2. [Test Structure](#test-structure)
3. [Setup and Installation](#setup-and-installation)
4. [Running Tests](#running-tests)
5. [Test Types](#test-types)
6. [Continuous Integration](#continuous-integration)
7. [Performance Testing](#performance-testing)
8. [Security Testing](#security-testing)
9. [Accessibility Testing](#accessibility-testing)
10. [Coverage Reports](#coverage-reports)
11. [Troubleshooting](#troubleshooting)

## Overview

The L&D Metrics Translator application includes a comprehensive testing suite that covers:

- **Unit Tests**: Testing individual components and functions
- **Integration Tests**: Testing component interactions and workflows
- **API Tests**: Testing REST API endpoints and responses
- **Performance Tests**: Load testing and performance benchmarks
- **Security Tests**: Vulnerability scanning and security validation
- **Accessibility Tests**: WCAG compliance and accessibility features
- **Code Quality**: Linting, formatting, and type checking

## Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Pytest configuration and fixtures
├── test_models.py              # Unit tests for database models
├── test_routes.py              # Unit tests for web routes
├── test_api.py                 # API endpoint tests
├── test_integration.py         # Integration tests
├── test_performance.py         # Performance and load tests
├── test_security.py            # Security vulnerability tests
└── test_accessibility.py       # Accessibility compliance tests

scripts/
├── run_tests.py               # Main test runner script
└── setup_test_env.py          # Test environment setup script

Configuration Files:
├── pytest.ini                 # Pytest configuration
├── pyproject.toml             # Tool configurations (black, isort, mypy, etc.)
├── .flake8                    # Flake8 linting configuration
├── locustfile.py              # Locust performance testing configuration
└── Makefile                   # Make commands for testing
```

## Setup and Installation

### Prerequisites

- Python 3.8 or higher
- Google Chrome (for Selenium tests)
- Git (for version control)

### Quick Setup

1. **Run the setup script:**
   ```bash
   python scripts/setup_test_env.py
   ```

2. **Or manually install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Manual Setup Steps

1. **Install testing dependencies:**
   ```bash
   pip install pytest pytest-flask pytest-cov pytest-mock
   pip install selenium webdriver-manager
   pip install locust memory-profiler psutil
   pip install flake8 black isort mypy bandit safety
   pip install axe-selenium-python
   ```

2. **Setup Chrome driver:**
   ```bash
   pip install webdriver-manager
   ```

3. **Create test directories:**
   ```bash
   mkdir -p htmlcov test-reports performance-reports security-reports
   ```

## Running Tests

### Using the Test Runner Script

The main test runner provides various options:

```bash
# Run all tests
python scripts/run_tests.py --all

# Run quick tests (unit + API + linting)
python scripts/run_tests.py --quick

# Run specific test types
python scripts/run_tests.py --unit
python scripts/run_tests.py --integration
python scripts/run_tests.py --api
python scripts/run_tests.py --performance
python scripts/run_tests.py --security
python scripts/run_tests.py --accessibility

# Run with coverage
python scripts/run_tests.py --coverage
```

### Using Make Commands

```bash
# Run all tests
make test

# Run quick tests
make test-quick

# Run specific test types
make test-unit
make test-integration
make test-api
make test-performance
make test-security
make test-accessibility

# Code quality checks
make lint
make format
make type-check
make security-scan

# Coverage report
make coverage
```

### Using Pytest Directly

```bash
# Run all tests
pytest tests/

# Run specific test files
pytest tests/test_models.py
pytest tests/test_api.py

# Run tests by marker
pytest tests/ -m unit
pytest tests/ -m integration
pytest tests/ -m performance

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

## Test Types

### Unit Tests

Test individual components in isolation:

```bash
# Run unit tests
pytest tests/ -m unit -v

# Specific unit test files
pytest tests/test_models.py
pytest tests/test_routes.py
```

**Coverage:**
- Database models and their methods
- Route handlers and form validation
- Utility functions and helpers
- Business logic components

### Integration Tests

Test component interactions and workflows:

```bash
# Run integration tests
pytest tests/ -m integration -v
```

**Coverage:**
- End-to-end user workflows
- Database integration scenarios
- API integration testing
- Frontend-backend integration

### API Tests

Test REST API endpoints:

```bash
# Run API tests
pytest tests/ -m api -v
```

**Coverage:**
- All API endpoints (`/api/outcomes`, `/api/metrics`, etc.)
- Request/response validation
- Error handling
- Authentication and authorization
- Pagination and filtering

### Performance Tests

Test application performance and load handling:

```bash
# Run performance tests
pytest tests/ -m performance -v

# Load testing with Locust
make load-test
make stress-test

# Or directly with Locust
locust -f locustfile.py --host=http://127.0.0.1:5000
```

**Coverage:**
- Database query performance
- API response times
- Memory usage monitoring
- Concurrent request handling
- Load testing scenarios

### Security Tests

Test security vulnerabilities and compliance:

```bash
# Run security tests
pytest tests/ -m security -v

# Security scanning
make security-scan
bandit -r app/
safety check
```

**Coverage:**
- Input validation and sanitization
- SQL injection protection
- XSS protection
- Authentication security
- Session management
- Dependency vulnerabilities

### Accessibility Tests

Test WCAG compliance and accessibility features:

```bash
# Run accessibility tests (requires Chrome)
pytest tests/ -m accessibility -v
```

**Coverage:**
- WCAG 2.1 Level AA compliance
- Screen reader compatibility
- Keyboard navigation
- Color contrast validation
- Semantic HTML structure
- Form accessibility

## Continuous Integration

The project includes GitHub Actions workflows for automated testing:

### CI Pipeline (`.github/workflows/ci.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`

**Jobs:**
1. **Test Matrix**: Python 3.9, 3.10, 3.11
2. **Code Quality**: Linting, formatting, type checking
3. **Unit & Integration Tests**: Core functionality testing
4. **Security Scanning**: Vulnerability detection
5. **Performance Testing**: Load and performance validation
6. **Accessibility Testing**: WCAG compliance checking

**Artifacts:**
- Test reports
- Coverage reports
- Security scan results
- Performance metrics

### Local CI Simulation

```bash
# Run the same checks as CI
make ci

# Or step by step
make format-check
make lint
make type-check
make test-quick
make security-scan
```

## Performance Testing

### Locust Load Testing

The project includes comprehensive Locust configuration:

```bash
# Light load test
locust -f locustfile.py --host=http://127.0.0.1:5000 -u 10 -r 2 -t 5m

# Normal load test
locust -f locustfile.py --host=http://127.0.0.1:5000 -u 50 -r 5 -t 10m

# Heavy load test
locust -f locustfile.py --host=http://127.0.0.1:5000 -u 100 -r 10 -t 15m

# Stress test
locust -f locustfile.py --host=http://127.0.0.1:5000 -u 200 -r 20 -t 20m
```

### User Scenarios

- **Regular Users**: Browse outcomes, use translator, search functionality
- **API Users**: Heavy API usage patterns
- **Mobile Users**: Mobile-specific usage patterns
- **Admin Users**: Administrative functionality testing

### Performance Metrics

- Response time percentiles (50th, 95th, 99th)
- Requests per second (RPS)
- Error rates
- Memory usage
- Database query performance

## Security Testing

### Automated Security Scanning

```bash
# Bandit - Python security linter
bandit -r app/ -f json -o bandit-report.json

# Safety - Dependency vulnerability scanner
safety check --json --output safety-report.json

# Combined security scan
make security-scan
```

### Security Test Coverage

- **Input Validation**: SQL injection, XSS, command injection
- **Authentication**: Password security, session management
- **Authorization**: Access control, privilege escalation
- **Data Protection**: Sensitive data exposure, information disclosure
- **Infrastructure**: Security headers, HTTPS, configuration

### Security Best Practices

- Regular dependency updates
- Secure coding practices
- Input sanitization
- Output encoding
- Proper error handling
- Secure session management

## Accessibility Testing

### Automated Accessibility Testing

Uses `axe-selenium-python` for WCAG compliance testing:

```bash
# Run accessibility tests
pytest tests/ -m accessibility -v
```

### Manual Accessibility Testing

1. **Keyboard Navigation**: Tab through all interactive elements
2. **Screen Reader**: Test with NVDA, JAWS, or VoiceOver
3. **Color Contrast**: Verify sufficient contrast ratios
4. **Zoom Testing**: Test at 200% zoom level
5. **Mobile Accessibility**: Test on mobile devices

### Accessibility Standards

- **WCAG 2.1 Level AA**: Target compliance level
- **Section 508**: US federal accessibility requirements
- **EN 301 549**: European accessibility standard

## Coverage Reports

### Generating Coverage Reports

```bash
# HTML coverage report
pytest tests/ --cov=app --cov-report=html

# Terminal coverage report
pytest tests/ --cov=app --cov-report=term-missing

# XML coverage report (for CI)
pytest tests/ --cov=app --cov-report=xml

# Combined reports
make coverage
```

### Coverage Targets

- **Minimum Coverage**: 80%
- **Target Coverage**: 90%
- **Critical Paths**: 95%+

### Coverage Analysis

- View detailed reports in `htmlcov/index.html`
- Identify uncovered code paths
- Focus on critical business logic
- Exclude test files and migrations

## Troubleshooting

### Common Issues

#### 1. Chrome Driver Issues

**Problem**: Selenium tests fail with Chrome driver errors

**Solutions:**
```bash
# Update Chrome driver
pip install --upgrade webdriver-manager

# Install Chrome (Ubuntu/Debian)
sudo apt-get install google-chrome-stable

# Install Chrome (macOS)
brew install --cask google-chrome
```

#### 2. Database Connection Issues

**Problem**: Tests fail with database connection errors

**Solutions:**
```bash
# Check database configuration
export FLASK_ENV=testing
export SQLALCHEMY_DATABASE_URI=sqlite:///:memory:

# Initialize test database
python init_db.py
```

#### 3. Import Errors

**Problem**: Module import errors in tests

**Solutions:**
```bash
# Add project root to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or use pytest with proper path
python -m pytest tests/
```

#### 4. Performance Test Timeouts

**Problem**: Performance tests timeout or fail

**Solutions:**
```bash
# Increase timeout values
pytest tests/ -m performance --timeout=600

# Run with fewer concurrent users
locust -f locustfile.py -u 10 -r 1
```

#### 5. Accessibility Test Failures

**Problem**: Accessibility tests fail to start

**Solutions:**
```bash
# Ensure Chrome is installed and accessible
google-chrome --version

# Install missing dependencies
pip install axe-selenium-python

# Run in headless mode
export CHROME_OPTIONS="--headless --no-sandbox"
```

### Debug Mode

Enable debug output for troubleshooting:

```bash
# Verbose pytest output
pytest tests/ -v -s

# Debug specific test
pytest tests/test_models.py::TestLDOutcome::test_create_outcome -v -s

# Show all print statements
pytest tests/ -s --capture=no
```

### Log Analysis

Check application logs during testing:

```bash
# Enable debug logging
export FLASK_DEBUG=1
export LOG_LEVEL=DEBUG

# View logs
tail -f app.log
```

## Best Practices

### Writing Tests

1. **Follow AAA Pattern**: Arrange, Act, Assert
2. **Use Descriptive Names**: Clear test method names
3. **Test One Thing**: Each test should verify one behavior
4. **Use Fixtures**: Reuse common test setup
5. **Mock External Dependencies**: Isolate units under test

### Test Organization

1. **Group Related Tests**: Use test classes
2. **Use Markers**: Tag tests by type and purpose
3. **Maintain Test Data**: Keep test data minimal and focused
4. **Document Complex Tests**: Add docstrings for complex scenarios

### Performance Considerations

1. **Parallel Execution**: Use `pytest-xdist` for faster runs
2. **Test Isolation**: Ensure tests don't interfere with each other
3. **Resource Cleanup**: Clean up test data and resources
4. **Selective Testing**: Run only relevant tests during development

### Maintenance

1. **Regular Updates**: Keep testing dependencies updated
2. **Review Coverage**: Regularly review and improve coverage
3. **Update Test Data**: Keep test scenarios current
4. **Monitor Performance**: Track test execution times

## Contributing

When contributing to the project:

1. **Write Tests First**: Follow TDD practices
2. **Maintain Coverage**: Don't decrease overall coverage
3. **Run Full Suite**: Ensure all tests pass before submitting
4. **Update Documentation**: Update this README for new test types
5. **Follow Standards**: Use consistent testing patterns

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Flask Testing](https://flask.palletsprojects.com/en/2.0.x/testing/)
- [Selenium Documentation](https://selenium-python.readthedocs.io/)
- [Locust Documentation](https://docs.locust.io/)
- [WCAG Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)

---

For questions or issues with testing, please refer to the project's issue tracker or contact the development team.
