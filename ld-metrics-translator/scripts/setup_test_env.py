#!/usr/bin/env python3
"""
Setup script for test environment.
This script prepares the testing environment and installs necessary dependencies.
"""
import os
import sys
import subprocess
import platform
from pathlib import Path


def run_command(command, description, check=True):
    """Run a command and handle errors."""
    print(f"\n{description}...")
    print(f"Running: {' '.join(command)}")
    
    try:
        result = subprocess.run(command, check=check, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed")
        print(f"Error: {e}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"✗ Command not found: {command[0]}")
        return False


def check_python_version():
    """Check Python version."""
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("✗ Python 3.8 or higher is required")
        return False
    
    print("✓ Python version is compatible")
    return True


def install_dependencies():
    """Install test dependencies."""
    print("\nInstalling dependencies...")
    
    # Upgrade pip first
    if not run_command([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'], 
                      "Upgrading pip"):
        return False
    
    # Install main dependencies
    if not run_command([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                      "Installing main dependencies"):
        return False
    
    return True


def setup_chrome_driver():
    """Setup Chrome driver for Selenium tests."""
    print("\nSetting up Chrome driver for Selenium tests...")
    
    system = platform.system().lower()
    
    if system == "windows":
        # Check if Chrome is installed
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        ]
        
        chrome_found = any(os.path.exists(path) for path in chrome_paths)
        
        if not chrome_found:
            print("⚠ Google Chrome not found. Please install Chrome for Selenium tests.")
            print("Download from: https://www.google.com/chrome/")
            return False
        
        # Install webdriver-manager for automatic driver management
        if run_command([sys.executable, '-m', 'pip', 'install', 'webdriver-manager'], 
                      "Installing webdriver-manager"):
            print("✓ Chrome driver setup completed")
            return True
    
    elif system in ["linux", "darwin"]:  # Linux or macOS
        # Check if Chrome/Chromium is installed
        chrome_commands = ["google-chrome", "chromium-browser", "chromium"]
        chrome_found = False
        
        for cmd in chrome_commands:
            if run_command(["which", cmd], f"Checking for {cmd}", check=False):
                chrome_found = True
                break
        
        if not chrome_found:
            print("⚠ Chrome/Chromium not found. Please install for Selenium tests.")
            if system == "linux":
                print("Install with: sudo apt-get install chromium-browser")
            elif system == "darwin":
                print("Install with: brew install --cask google-chrome")
            return False
        
        # Install webdriver-manager
        if run_command([sys.executable, '-m', 'pip', 'install', 'webdriver-manager'], 
                      "Installing webdriver-manager"):
            print("✓ Chrome driver setup completed")
            return True
    
    return False


def create_test_directories():
    """Create necessary test directories."""
    print("\nCreating test directories...")
    
    directories = [
        "htmlcov",
        "test-reports",
        "performance-reports",
        "security-reports"
    ]
    
    for directory in directories:
        path = Path(directory)
        path.mkdir(exist_ok=True)
        print(f"✓ Created directory: {directory}")
    
    return True


def setup_git_hooks():
    """Setup git hooks for pre-commit testing."""
    print("\nSetting up git hooks...")
    
    git_dir = Path(".git")
    if not git_dir.exists():
        print("⚠ Not a git repository. Skipping git hooks setup.")
        return True
    
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    
    # Pre-commit hook
    pre_commit_hook = hooks_dir / "pre-commit"
    pre_commit_content = """#!/bin/sh
# Pre-commit hook for L&D Metrics Translator

echo "Running pre-commit tests..."

# Run quick tests
python scripts/run_tests.py --quick

if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi

echo "All tests passed. Proceeding with commit."
exit 0
"""
    
    with open(pre_commit_hook, 'w') as f:
        f.write(pre_commit_content)
    
    # Make executable (Unix-like systems)
    if platform.system() != "Windows":
        os.chmod(pre_commit_hook, 0o755)
    
    print("✓ Git pre-commit hook created")
    return True


def create_test_config():
    """Create test configuration files."""
    print("\nCreating test configuration...")
    
    # Create test environment file
    test_env_content = """# Test Environment Configuration
FLASK_ENV=testing
TESTING=True
WTF_CSRF_ENABLED=False
SQLALCHEMY_DATABASE_URI=sqlite:///:memory:
SECRET_KEY=test-secret-key-for-testing-only

# Disable external services in tests
DISABLE_EMAIL=True
DISABLE_LOGGING=True

# Test-specific settings
TEST_TIMEOUT=300
SELENIUM_TIMEOUT=10
PERFORMANCE_THRESHOLD=5.0
"""
    
    with open('.env.test', 'w') as f:
        f.write(test_env_content)
    
    print("✓ Test environment configuration created")
    
    # Create pytest configuration if it doesn't exist
    if not Path('pytest.ini').exists():
        pytest_content = """[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --tb=short
    --strict-markers
    --disable-warnings
markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance tests
    security: Security tests
    accessibility: Accessibility tests
    slow: Slow running tests
    database: Database tests
    api: API tests
    frontend: Frontend tests
"""
        
        with open('pytest.ini', 'w') as f:
            f.write(pytest_content)
        
        print("✓ Pytest configuration created")
    
    return True


def verify_installation():
    """Verify that all components are properly installed."""
    print("\nVerifying installation...")
    
    # Check Python packages
    packages_to_check = [
        'pytest',
        'pytest-flask',
        'pytest-cov',
        'selenium',
        'requests',
        'flake8',
        'black',
        'isort',
        'bandit',
        'safety',
        'locust'
    ]
    
    missing_packages = []
    
    for package in packages_to_check:
        try:
            __import__(package.replace('-', '_'))
            print(f"✓ {package} is installed")
        except ImportError:
            print(f"✗ {package} is missing")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\nMissing packages: {', '.join(missing_packages)}")
        print("Run: pip install " + " ".join(missing_packages))
        return False
    
    # Test database connection
    try:
        from app import create_app, db
        app = create_app('testing')
        with app.app_context():
            db.create_all()
        print("✓ Database connection test passed")
    except Exception as e:
        print(f"✗ Database connection test failed: {e}")
        return False
    
    print("\n✓ All components verified successfully")
    return True


def main():
    """Main setup function."""
    print("="*60)
    print("L&D METRICS TRANSLATOR - TEST ENVIRONMENT SETUP")
    print("="*60)
    
    # Change to project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    print(f"Project root: {project_root.absolute()}")
    
    # Setup steps
    steps = [
        ("Checking Python version", check_python_version),
        ("Installing dependencies", install_dependencies),
        ("Setting up Chrome driver", setup_chrome_driver),
        ("Creating test directories", create_test_directories),
        ("Setting up git hooks", setup_git_hooks),
        ("Creating test configuration", create_test_config),
        ("Verifying installation", verify_installation)
    ]
    
    failed_steps = []
    
    for step_name, step_function in steps:
        print(f"\n{'-'*40}")
        print(f"STEP: {step_name}")
        print(f"{'-'*40}")
        
        try:
            if not step_function():
                failed_steps.append(step_name)
        except Exception as e:
            print(f"✗ {step_name} failed with exception: {e}")
            failed_steps.append(step_name)
    
    # Summary
    print("\n" + "="*60)
    print("SETUP SUMMARY")
    print("="*60)
    
    if failed_steps:
        print(f"✗ Setup completed with {len(failed_steps)} failed steps:")
        for step in failed_steps:
            print(f"  - {step}")
        print("\nPlease address the failed steps before running tests.")
        sys.exit(1)
    else:
        print("✓ Setup completed successfully!")
        print("\nYou can now run tests using:")
        print("  python scripts/run_tests.py --quick    # Quick tests")
        print("  python scripts/run_tests.py --all      # Full test suite")
        print("  python scripts/run_tests.py --help     # See all options")
        sys.exit(0)


if __name__ == '__main__':
    main()
