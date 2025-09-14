# Installation Guide

This guide provides step-by-step instructions for installing and running the L&D Metrics Translator on any PC.

## System Requirements

### Minimum Requirements
- **Operating System**: Windows 10/11, macOS 10.15+, or Linux (Ubuntu 20.04+)
- **RAM**: 4GB (8GB recommended)
- **Storage**: 2GB free space
- **Internet**: Required for initial setup and updates

### Required Software
- **Python 3.11 or higher** (Required)
- **Git** (Recommended for updates)
- **Web Browser** (Chrome, Firefox, Safari, or Edge)

## Quick Installation (Windows)

### Option 1: Automated Setup Script

1. **Download the project** (if you haven't already)
2. **Open Command Prompt** as Administrator
3. **Navigate to the project folder**:
   ```cmd
   cd path\to\ld-metrics-translator
   ```
4. **Run the setup script**:
   ```cmd
   setup_windows.bat
   ```
5. **Follow the on-screen instructions**

The script will automatically:
- Check Python installation
- Create a virtual environment
- Install all dependencies
- Set up the database
- Create an admin user
- Configure the application

### Option 2: Manual Installation

If the automated script doesn't work, follow these manual steps:

## Manual Installation Instructions

### Step 1: Install Python

1. **Download Python 3.11+** from [python.org](https://python.org)
2. **Run the installer**
3. **IMPORTANT**: Check "Add Python to PATH" during installation
4. **Verify installation**:
   ```cmd
   python --version
   ```
   Should show Python 3.11.x or higher

### Step 2: Download the Application

**Option A: Download ZIP**
1. Download the project as a ZIP file
2. Extract to a folder (e.g., `C:\Users\YourName\ld-metrics-translator`)

**Option B: Use Git (Recommended)**
1. Install Git from [git-scm.com](https://git-scm.com)
2. Open Command Prompt
3. Run:
   ```cmd
   git clone https://github.com/your-org/ld-metrics-translator.git
   cd ld-metrics-translator
   ```

### Step 3: Set Up Virtual Environment

1. **Open Command Prompt** in the project folder
2. **Create virtual environment**:
   ```cmd
   python -m venv venv
   ```
3. **Activate virtual environment**:
   
   **Windows:**
   ```cmd
   venv\Scripts\activate
   ```
   
   **macOS/Linux:**
   ```bash
   source venv/bin/activate
   ```

You should see `(venv)` at the beginning of your command prompt.

### Step 4: Install Dependencies

With the virtual environment activated:

```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

This will install all required Python packages.

### Step 5: Configure the Application

1. **Copy the environment template**:
   ```cmd
   copy .env.example .env
   ```
   
2. **Edit the .env file** (optional for basic usage):
   - Open `.env` in any text editor
   - The default settings work for local development
   - For production, update the SECRET_KEY and other settings

### Step 6: Set Up the Database

Run these commands in order:

```cmd
python init_db.py
python seed_database.py
python setup_admin.py
```

When prompted for admin credentials, enter:
- Username (e.g., "admin")
- Email address
- Password (remember this!)

### Step 7: Start the Application

```cmd
python run.py
```

You should see output like:
```
* Running on http://127.0.0.1:5000
* Debug mode: on
```

### Step 8: Access the Application

1. **Open your web browser**
2. **Go to**: http://localhost:5000
3. **You should see the L&D Metrics Translator homepage**

## Accessing Admin Features

1. **Go to**: http://localhost:5000/admin
2. **Login** with the credentials you created in Step 6
3. **Manage metrics** and application settings

## Troubleshooting

### Common Issues

**"Python is not recognized"**
- Python is not installed or not in PATH
- Reinstall Python and check "Add to PATH"
- Restart Command Prompt after installation

**"pip is not recognized"**
- Usually fixed by upgrading Python
- Try: `python -m pip install --upgrade pip`

**"Permission denied" errors**
- Run Command Prompt as Administrator
- Check file permissions in the project folder

**Database errors**
- Delete the `ld_metrics.db` file and run setup again
- Ensure no other instance is running

**Port 5000 already in use**
- Another application is using port 5000
- Kill other processes or change port in `run.py`

**Virtual environment issues**
- Delete the `venv` folder and recreate it
- Ensure you're in the correct directory

### Getting Help

**Check the logs**:
- Look in the `logs/` folder for error messages
- Check the Command Prompt output for errors

**Verify installation**:
```cmd
python -c "import flask; print('Flask installed successfully')"
```

**Test database connection**:
```cmd
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.session.execute('SELECT 1'); print('Database OK')"
```

## Advanced Configuration

### Using PostgreSQL (Production)

For production use, PostgreSQL is recommended:

1. **Install PostgreSQL** from [postgresql.org](https://postgresql.org)
2. **Create database**:
   ```sql
   CREATE DATABASE ldmetrics;
   CREATE USER ldmetrics_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE ldmetrics TO ldmetrics_user;
   ```
3. **Update .env file**:
   ```
   DATABASE_URL=postgresql://ldmetrics_user:your_password@localhost/ldmetrics
   ```

### Docker Installation (Alternative)

If you have Docker installed:

```cmd
docker-compose up --build
```

This will start the application with all dependencies.

## Updating the Application

### With Git:
```cmd
git pull origin main
pip install -r requirements.txt
python init_db.py  # If database changes
```

### Manual:
1. Download the latest version
2. Replace files (keep your `.env` file)
3. Reinstall dependencies: `pip install -r requirements.txt`

## Uninstalling

To completely remove the application:

1. **Deactivate virtual environment**: `deactivate`
2. **Delete the project folder**
3. **Remove Python** (if no longer needed)

## Performance Tips

### For Better Performance:
- Use PostgreSQL instead of SQLite for large datasets
- Enable Redis for caching (see production setup)
- Use a proper web server (Nginx + Gunicorn) for production

### For Development:
- Keep the virtual environment activated while working
- Use `python run.py` for development
- Check logs in `logs/` folder for debugging

## Security Notes

### For Production Use:
- Change the SECRET_KEY in `.env`
- Use HTTPS (SSL certificates)
- Set up proper firewall rules
- Regular backups of the database
- Keep Python and dependencies updated

### Default Credentials:
- Change admin password after first login
- Use strong passwords for production
- Consider two-factor authentication for admin accounts

## Support

### Self-Help Resources:
- [User Guide](docs/user-guide.md) - How to use the application
- [API Documentation](docs/api.md) - API reference
- [Deployment Guide](docs/deployment.md) - Production setup
- [Developer Guide](docs/developer.md) - Technical details

### Getting Support:
- **Email**: support@ldmetrics.com
- **GitHub Issues**: Report bugs and request features
- **Documentation**: Check the `docs/` folder for detailed guides

### Community:
- Share your experience with other users
- Contribute improvements and suggestions
- Help others with installation issues

---

**Congratulations!** You now have the L&D Metrics Translator running on your PC. Start exploring the metrics database and discover how to measure the impact of your learning and development initiatives!
