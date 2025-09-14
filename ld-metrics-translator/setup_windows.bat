@echo off
REM L&D Metrics Translator - Windows Setup Script
REM This script sets up the application on Windows systems

echo ========================================
echo L&D Metrics Translator Setup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11 or higher from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo Python found:
python --version
echo.

REM Check Python version
python -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.11 or higher is required
    echo Please upgrade your Python installation
    pause
    exit /b 1
)

echo Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo Setting up environment configuration...
if not exist .env (
    copy .env.example .env
    echo Created .env file from template
    echo Please edit .env file with your configuration before running the application
) else (
    echo .env file already exists
)

echo Creating necessary directories...
if not exist logs mkdir logs
if not exist instance mkdir instance
if not exist backups mkdir backups

echo Initializing database...
python init_db.py
if errorlevel 1 (
    echo ERROR: Failed to initialize database
    pause
    exit /b 1
)

echo Seeding database with sample data...
python seed_database.py
if errorlevel 1 (
    echo ERROR: Failed to seed database
    pause
    exit /b 1
)

echo Setting up admin user...
python setup_admin.py
if errorlevel 1 (
    echo ERROR: Failed to setup admin user
    pause
    exit /b 1
)

echo.
echo ========================================
echo Setup completed successfully!
echo ========================================
echo.
echo To start the application:
echo 1. Activate virtual environment: venv\Scripts\activate.bat
echo 2. Run the application: python run.py
echo 3. Open your browser to: http://localhost:5000
echo.
echo For production deployment, see docs/deployment.md
echo.
pause
