# Makefile for L&D Metrics Translator

.PHONY: help install test test-quick test-unit test-integration test-api test-performance test-security test-accessibility lint format type-check security-scan clean setup dev run

# Default target
help:
	@echo "L&D Metrics Translator - Available Commands"
	@echo "==========================================="
	@echo ""
	@echo "Setup and Installation:"
	@echo "  setup          - Set up the development environment"
	@echo "  install        - Install dependencies"
	@echo ""
	@echo "Development:"
	@echo "  dev            - Start development server"
	@echo "  run            - Run the application"
	@echo ""
	@echo "Testing:"
	@echo "  test           - Run all tests"
	@echo "  test-quick     - Run quick tests (unit, api, lint)"
	@echo "  test-unit      - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-api       - Run API tests only"
	@echo "  test-performance - Run performance tests only"
	@echo "  test-security  - Run security tests only"
	@echo "  test-accessibility - Run accessibility tests only"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint           - Run linting (flake8)"
	@echo "  format         - Format code (black, isort)"
	@echo "  type-check     - Run type checking (mypy)"
	@echo "  security-scan  - Run security scanning (bandit, safety)"
	@echo ""
	@echo "Utilities:"
	@echo "  clean          - Clean up generated files"
	@echo "  coverage       - Generate coverage report"
	@echo ""

# Setup and Installation
setup:
	@echo "Setting up development environment..."
	python scripts/setup_test_env.py

install:
	@echo "Installing dependencies..."
	python -m pip install --upgrade pip
	pip install -r requirements.txt

# Development
dev:
	@echo "Starting development server..."
	python run.py

run:
	@echo "Running application..."
	python run.py

# Testing
test:
	@echo "Running all tests..."
	python scripts/run_tests.py --all

test-quick:
	@echo "Running quick tests..."
	python scripts/run_tests.py --quick

test-unit:
	@echo "Running unit tests..."
	python scripts/run_tests.py --unit

test-integration:
	@echo "Running integration tests..."
	python scripts/run_tests.py --integration

test-api:
	@echo "Running API tests..."
	python scripts/run_tests.py --api

test-performance:
	@echo "Running performance tests..."
	python scripts/run_tests.py --performance

test-security:
	@echo "Running security tests..."
	python scripts/run_tests.py --security

test-accessibility:
	@echo "Running accessibility tests..."
	python scripts/run_tests.py --accessibility

# Code Quality
lint:
	@echo "Running linting..."
	flake8 app/ tests/
	@echo "Linting completed."

format:
	@echo "Formatting code..."
	black app/ tests/
	isort app/ tests/
	@echo "Code formatting completed."

format-check:
	@echo "Checking code formatting..."
	black --check app/ tests/
	isort --check-only app/ tests/

type-check:
	@echo "Running type checking..."
	mypy app/

security-scan:
	@echo "Running security scans..."
	bandit -r app/ -f json -o bandit-report.json
	safety check --json --output safety-report.json
	@echo "Security scanning completed."

# Coverage
coverage:
	@echo "Generating coverage report..."
	python -m pytest tests/ --cov=app --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/"

# Database
init-db:
	@echo "Initializing database..."
	python init_db.py

seed-db:
	@echo "Seeding database..."
	python seed_database.py

setup-admin:
	@echo "Setting up admin user..."
	python setup_admin.py

# Performance Testing
load-test:
	@echo "Running load tests with Locust..."
	locust -f locustfile.py --host=http://127.0.0.1:5000 -u 50 -r 5 -t 10m --headless

stress-test:
	@echo "Running stress tests with Locust..."
	locust -f locustfile.py --host=http://127.0.0.1:5000 -u 100 -r 10 -t 15m --headless

# Cleanup
clean:
	@echo "Cleaning up generated files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf dist/
	rm -rf build/
	rm -f bandit-report.json
	rm -f safety-report.json
	rm -f test-report.html
	@echo "Cleanup completed."

# Docker (if using Docker)
docker-build:
	@echo "Building Docker image..."
	docker build -t ld-metrics-translator .

docker-run:
	@echo "Running Docker container..."
	docker run -p 5000:5000 ld-metrics-translator

docker-test:
	@echo "Running tests in Docker..."
	docker run --rm ld-metrics-translator python scripts/run_tests.py --quick

# Production
deploy-staging:
	@echo "Deploying to staging..."
	# Add staging deployment commands here

deploy-production:
	@echo "Deploying to production..."
	# Add production deployment commands here

# Git hooks
install-hooks:
	@echo "Installing git hooks..."
	cp scripts/pre-commit .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit
	@echo "Git hooks installed."

# Documentation
docs:
	@echo "Generating documentation..."
	# Add documentation generation commands here

# Monitoring
monitor:
	@echo "Starting application monitoring..."
	# Add monitoring commands here

# Backup
backup-db:
	@echo "Backing up database..."
	# Add database backup commands here

# Environment management
create-env:
	@echo "Creating virtual environment..."
	python -m venv venv

activate-env:
	@echo "To activate virtual environment, run:"
	@echo "Windows: venv\\Scripts\\activate"
	@echo "Unix/MacOS: source venv/bin/activate"

# All-in-one commands
quick-start: install init-db seed-db setup-admin
	@echo "Quick start completed. Run 'make dev' to start the server."

full-test: format lint type-check test security-scan
	@echo "Full test suite completed."

ci: format-check lint type-check test-quick security-scan
	@echo "CI pipeline completed."

# Help for specific test types
test-help:
	@echo "Test Commands Help"
	@echo "=================="
	@echo ""
	@echo "test           - Run complete test suite (all test types)"
	@echo "test-quick     - Run essential tests (unit + API + linting)"
	@echo "test-unit      - Run unit tests for models, utilities, etc."
	@echo "test-integration - Run integration tests (database + API + web)"
	@echo "test-api       - Run API endpoint tests"
	@echo "test-performance - Run performance and load tests"
	@echo "test-security  - Run security vulnerability tests"
	@echo "test-accessibility - Run accessibility compliance tests"
	@echo ""
	@echo "Coverage:"
	@echo "coverage       - Generate HTML coverage report"
	@echo ""
	@echo "Performance:"
	@echo "load-test      - Run load testing with Locust"
	@echo "stress-test    - Run stress testing with Locust"
