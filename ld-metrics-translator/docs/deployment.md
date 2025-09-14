# Deployment Guide

This guide covers deploying the L&D Metrics Translator application in various environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Database Setup](#database-setup)
4. [Docker Deployment](#docker-deployment)
5. [Traditional Server Deployment](#traditional-server-deployment)
6. [Cloud Platform Deployment](#cloud-platform-deployment)
7. [Monitoring and Maintenance](#monitoring-and-maintenance)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

**Minimum Requirements:**
- CPU: 2 cores
- RAM: 4GB
- Storage: 20GB
- OS: Linux (Ubuntu 20.04+), Windows Server 2019+, macOS 10.15+

**Recommended for Production:**
- CPU: 4+ cores
- RAM: 8GB+
- Storage: 50GB+ SSD
- OS: Linux (Ubuntu 22.04 LTS)

### Software Dependencies

- **Python**: 3.11 or higher
- **Database**: PostgreSQL 13+ (recommended) or SQLite (development only)
- **Web Server**: Nginx (recommended) or Apache
- **Process Manager**: Gunicorn (included) or uWSGI
- **Container Runtime**: Docker 20.10+ and Docker Compose 2.0+ (optional)

## Environment Configuration

### 1. Create Environment File

Copy the example environment file and customize it:

```bash
cp .env.example .env.production
```

### 2. Essential Production Settings

Edit `.env.production` with these critical settings:

```bash
# Application Environment
FLASK_ENV=production
SECRET_KEY=your-very-long-random-secret-key-here

# Database (PostgreSQL recommended for production)
DATABASE_URL=postgresql://username:password@localhost:5432/ldmetrics

# Security
SESSION_COOKIE_SECURE=true
WTF_CSRF_ENABLED=true

# Logging
LOG_LEVEL=WARNING
LOG_FILE=/var/log/ldmetrics/app.log

# Email for Error Notifications
MAIL_SERVER=smtp.your-provider.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@company.com
MAIL_PASSWORD=your-app-password
ADMINS=admin@company.com,support@company.com

# Monitoring (Optional but Recommended)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# Rate Limiting (Redis recommended for production)
REDIS_URL=redis://localhost:6379/0
```

### 3. Generate Secret Key

Generate a secure secret key:

```python
import secrets
print(secrets.token_urlsafe(32))
```

## Database Setup

### PostgreSQL Setup (Recommended)

1. **Install PostgreSQL:**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install postgresql postgresql-contrib
   
   # CentOS/RHEL
   sudo yum install postgresql-server postgresql-contrib
   sudo postgresql-setup initdb
   ```

2. **Create Database and User:**
   ```bash
   sudo -u postgres psql
   ```
   ```sql
   CREATE DATABASE ldmetrics;
   CREATE USER ldmetrics_user WITH PASSWORD 'secure_password';
   GRANT ALL PRIVILEGES ON DATABASE ldmetrics TO ldmetrics_user;
   \q
   ```

3. **Configure PostgreSQL:**
   Edit `/etc/postgresql/*/main/postgresql.conf`:
   ```
   listen_addresses = 'localhost'
   max_connections = 100
   shared_buffers = 256MB
   ```

   Edit `/etc/postgresql/*/main/pg_hba.conf`:
   ```
   local   ldmetrics    ldmetrics_user                     md5
   host    ldmetrics    ldmetrics_user    127.0.0.1/32     md5
   ```

4. **Restart PostgreSQL:**
   ```bash
   sudo systemctl restart postgresql
   sudo systemctl enable postgresql
   ```

### Database Migration

```bash
# Set environment
export FLASK_ENV=production

# Initialize and migrate database
python init_db.py
python seed_database.py

# Create admin user
python setup_admin.py
```

## Docker Deployment

### 1. Quick Docker Deployment

For a simple deployment with all services:

```bash
# Clone repository
git clone https://github.com/your-org/ld-metrics-translator.git
cd ld-metrics-translator

# Configure environment
cp .env.example .env.production
# Edit .env.production with your settings

# Deploy
docker-compose --env-file .env.production up -d
```

### 2. Production Docker Deployment

1. **Create production docker-compose file:**
   ```yaml
   # docker-compose.prod.yml
   version: '3.8'
   
   services:
     web:
       build: .
       restart: unless-stopped
       environment:
         - FLASK_ENV=production
       env_file:
         - .env.production
       depends_on:
         - db
         - redis
       volumes:
         - ./logs:/app/logs
         - ./backups:/app/backups
       networks:
         - app-network
   
     db:
       image: postgres:15-alpine
       restart: unless-stopped
       environment:
         - POSTGRES_DB=ldmetrics
         - POSTGRES_USER=ldmetrics
         - POSTGRES_PASSWORD=${DB_PASSWORD}
       volumes:
         - postgres_data:/var/lib/postgresql/data
         - ./backups:/backups
       networks:
         - app-network
   
     redis:
       image: redis:7-alpine
       restart: unless-stopped
       volumes:
         - redis_data:/data
       networks:
         - app-network
   
     nginx:
       image: nginx:alpine
       restart: unless-stopped
       ports:
         - "80:80"
         - "443:443"
       volumes:
         - ./nginx.prod.conf:/etc/nginx/nginx.conf:ro
         - ./ssl:/etc/nginx/ssl:ro
         - ./static:/var/www/static:ro
       depends_on:
         - web
       networks:
         - app-network
   
   volumes:
     postgres_data:
     redis_data:
   
   networks:
     app-network:
       driver: bridge
   ```

2. **Deploy:**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

### 3. SSL Certificate Setup

For HTTPS support, obtain SSL certificates:

```bash
# Using Let's Encrypt with Certbot
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Traditional Server Deployment

### 1. System Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3.11 python3.11-venv python3.11-dev
sudo apt install nginx postgresql redis-server
sudo apt install build-essential libpq-dev
```

### 2. Application Setup

```bash
# Create application user
sudo useradd -m -s /bin/bash ldmetrics
sudo su - ldmetrics

# Clone and setup application
git clone https://github.com/your-org/ld-metrics-translator.git
cd ld-metrics-translator

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env.production
# Edit .env.production

# Initialize database
python init_db.py
python seed_database.py
python setup_admin.py
```

### 3. Systemd Service

Create `/etc/systemd/system/ldmetrics.service`:

```ini
[Unit]
Description=L&D Metrics Translator
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=ldmetrics
Group=ldmetrics
WorkingDirectory=/home/ldmetrics/ld-metrics-translator
Environment=PATH=/home/ldmetrics/ld-metrics-translator/venv/bin
EnvironmentFile=/home/ldmetrics/ld-metrics-translator/.env.production
ExecStart=/home/ldmetrics/ld-metrics-translator/venv/bin/gunicorn \
    --bind unix:/tmp/ldmetrics.sock \
    --workers 4 \
    --timeout 120 \
    --keep-alive 2 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --preload \
    --access-logfile /var/log/ldmetrics/access.log \
    --error-logfile /var/log/ldmetrics/error.log \
    run:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ldmetrics
sudo systemctl start ldmetrics
```

### 4. Nginx Configuration

Create `/etc/nginx/sites-available/ldmetrics`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # Static files
    location /static/ {
        alias /home/ldmetrics/ld-metrics-translator/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Application
    location / {
        proxy_pass http://unix:/tmp/ldmetrics.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/ldmetrics /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Cloud Platform Deployment

### AWS Deployment

1. **Using AWS Elastic Beanstalk:**
   ```bash
   # Install EB CLI
   pip install awsebcli
   
   # Initialize and deploy
   eb init
   eb create production
   eb deploy
   ```

2. **Using AWS ECS with Fargate:**
   - Use the provided `Dockerfile`
   - Create ECS task definition
   - Set up Application Load Balancer
   - Configure RDS for PostgreSQL
   - Use ElastiCache for Redis

### Google Cloud Platform

1. **Using Google Cloud Run:**
   ```bash
   # Build and deploy
   gcloud builds submit --tag gcr.io/PROJECT_ID/ldmetrics
   gcloud run deploy --image gcr.io/PROJECT_ID/ldmetrics --platform managed
   ```

2. **Using Google Kubernetes Engine:**
   - Use provided Kubernetes manifests
   - Configure Cloud SQL for PostgreSQL
   - Set up Cloud Memorystore for Redis

### Azure Deployment

1. **Using Azure Container Instances:**
   ```bash
   # Deploy container
   az container create \
     --resource-group myResourceGroup \
     --name ldmetrics \
     --image your-registry/ldmetrics:latest
   ```

## Monitoring and Maintenance

### 1. Health Monitoring

Set up monitoring for the health endpoint:

```bash
# Simple health check script
#!/bin/bash
curl -f http://localhost/api/health || exit 1
```

### 2. Log Rotation

Configure logrotate for application logs:

```bash
# /etc/logrotate.d/ldmetrics
/var/log/ldmetrics/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 ldmetrics ldmetrics
    postrotate
        systemctl reload ldmetrics
    endscript
}
```

### 3. Database Backups

Set up automated database backups:

```bash
#!/bin/bash
# /home/ldmetrics/backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -h localhost -U ldmetrics_user ldmetrics > /backups/ldmetrics_$DATE.sql
find /backups -name "ldmetrics_*.sql" -mtime +7 -delete
```

Add to crontab:
```bash
0 2 * * * /home/ldmetrics/backup.sh
```

### 4. Performance Monitoring

Monitor key metrics:
- Response times
- Error rates
- Database performance
- Memory usage
- Disk space

## Troubleshooting

### Common Issues

1. **Application won't start:**
   ```bash
   # Check logs
   sudo journalctl -u ldmetrics -f
   
   # Check configuration
   python -c "from config import config; print(config['production'])"
   ```

2. **Database connection errors:**
   ```bash
   # Test database connection
   psql -h localhost -U ldmetrics_user -d ldmetrics
   
   # Check PostgreSQL status
   sudo systemctl status postgresql
   ```

3. **Static files not loading:**
   ```bash
   # Check Nginx configuration
   sudo nginx -t
   
   # Check file permissions
   ls -la /home/ldmetrics/ld-metrics-translator/static/
   ```

4. **High memory usage:**
   ```bash
   # Monitor processes
   htop
   
   # Check Gunicorn workers
   ps aux | grep gunicorn
   ```

### Performance Tuning

1. **Database optimization:**
   ```sql
   -- Add indexes for common queries
   CREATE INDEX idx_metrics_outcome ON metrics(ld_outcome_id);
   CREATE INDEX idx_metrics_type ON metrics(metric_type_id);
   ```

2. **Gunicorn tuning:**
   ```bash
   # Calculate workers: (2 x CPU cores) + 1
   --workers 9  # For 4-core system
   ```

3. **Nginx caching:**
   ```nginx
   # Add to Nginx config
   location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg)$ {
       expires 1y;
       add_header Cache-Control "public, immutable";
   }
   ```

### Security Checklist

- [ ] SSL/TLS certificates configured
- [ ] Security headers enabled
- [ ] Database access restricted
- [ ] Application running as non-root user
- [ ] Firewall configured
- [ ] Regular security updates applied
- [ ] Backup procedures tested
- [ ] Monitoring and alerting configured

## Support

For deployment issues:
- Check the [troubleshooting section](#troubleshooting)
- Review application logs
- Consult the [GitHub issues](https://github.com/your-org/ld-metrics-translator/issues)
- Contact support at support@ldmetrics.com
