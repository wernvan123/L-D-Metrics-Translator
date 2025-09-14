#!/usr/bin/env python3
"""
Production startup script for L&D Metrics Translator
This script handles production environment setup and application startup.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_python_version():
    """Ensure Python version is compatible."""
    if sys.version_info < (3, 11):
        logger.error("Python 3.11 or higher is required")
        sys.exit(1)
    logger.info(f"Python version: {sys.version}")

def check_environment():
    """Check if required environment variables are set."""
    required_vars = [
        'SECRET_KEY',
        'DATABASE_URL',
        'FLASK_ENV'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please check your .env file or environment configuration")
        sys.exit(1)
    
    logger.info("Environment variables validated")

def check_database_connection():
    """Test database connectivity."""
    try:
        from app import create_app, db
        app = create_app(os.environ.get('FLASK_ENV', 'production'))
        
        with app.app_context():
            db.session.execute('SELECT 1')
            logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        sys.exit(1)

def ensure_directories():
    """Create necessary directories."""
    directories = [
        'logs',
        'instance',
        'backups'
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        logger.info(f"Directory ensured: {directory}")

def run_database_migrations():
    """Run database migrations if needed."""
    try:
        from flask_migrate import upgrade
        from app import create_app
        
        app = create_app(os.environ.get('FLASK_ENV', 'production'))
        with app.app_context():
            upgrade()
        logger.info("Database migrations completed")
    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        sys.exit(1)

def start_application():
    """Start the application with Gunicorn."""
    # Gunicorn configuration
    config = {
        'bind': '0.0.0.0:5000',
        'workers': os.cpu_count() * 2 + 1,
        'worker_class': 'sync',
        'timeout': 120,
        'keepalive': 2,
        'max_requests': 1000,
        'max_requests_jitter': 100,
        'preload_app': True,
        'access_logfile': 'logs/access.log',
        'error_logfile': 'logs/error.log',
        'log_level': 'info',
        'capture_output': True
    }
    
    # Build Gunicorn command
    cmd = ['gunicorn']
    for key, value in config.items():
        cmd.extend([f'--{key.replace("_", "-")}', str(value)])
    cmd.append('run:app')
    
    logger.info(f"Starting application with command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Application stopped by user")

def main():
    """Main startup sequence."""
    logger.info("Starting L&D Metrics Translator in production mode")
    
    # Pre-flight checks
    check_python_version()
    check_environment()
    ensure_directories()
    check_database_connection()
    run_database_migrations()
    
    # Start application
    start_application()

if __name__ == '__main__':
    main()
