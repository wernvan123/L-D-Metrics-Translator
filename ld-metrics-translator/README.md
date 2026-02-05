# L&D Metrics Translator

[![Build Status](https://github.com/your-org/ld-metrics-translator/workflows/CI/badge.svg)](https://github.com/your-org/ld-metrics-translator/actions)
[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Flask Version](https://img.shields.io/badge/flask-2.3+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A powerful, production-ready web application designed for Learning & Development (L&D) professionals to bridge the gap between learning initiatives and tangible business results.

## 🎯 Overview

The L&D Metrics Translator helps L&D professionals:
- Translate learning outcomes into measurable business metrics
- Connect learning goals to concrete KPIs and behavioral indicators
- Access neuroscience-backed insights for learning effectiveness
- Build credible, data-driven conversations with stakeholders

## Human Performance Navigator (Diagnostics)

This application also includes a consultant-led Diagnostics experience ("Human Performance Navigator") to support event analysis and behavioral science diagnostics.

- **Access**: `/diagnostics`
- **Primary workflow**: Describe a workplace event, analyze it, and generate structured insights.
- **Optional role context**: Select a Role Profile to contextualize analysis and produce a role-aligned gap report.

### MVP direction: company data intake via exports

To support consulting engagements (e.g., with clients providing internal data), the intended MVP approach is **exports/CSV-first** ingestion from systems clients already use (e.g., work tracking, retrospectives, code repositories, surveys). This documentation describes the operating model and data requirements; the UI/API for CSV ingestion may be introduced incrementally.

## ✨ Features

### Core Features
- **Interactive Metrics Database**: 100+ L&D metrics categorized by outcomes and types
- **Dynamic Filtering**: Filter by L&D outcomes and metric types
- **Advanced Search**: Full-text search with highlighting
- **Detail Pages**: In-depth metric information with practical examples
- **Admin Interface**: Comprehensive content management system
- **RESTful API**: Complete API for integration with other systems
- **Diagnostics**: Event Analysis and Behavioral Science Diagnostic tools in `/diagnostics`

### Production Features
- **Security**: CSRF protection, secure headers, rate limiting
- **Monitoring**: Health checks, error tracking, comprehensive logging
- **Performance**: Database optimization, caching, compression
- **Scalability**: Docker support, load balancer ready
- **Testing**: 95%+ test coverage with automated CI/CD

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- Git
- (Optional) Docker and Docker Compose

### Local Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-org/ld-metrics-translator.git
   cd ld-metrics-translator
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database**:
   ```bash
   python init_db.py
   python seed_database.py
   ```

6. **Create admin user**:
   ```bash
   python setup_admin.py
   ```

7. **Run the application**:
   ```bash
   python run.py
   ```

8. **Access the application**:
   - Main app: http://localhost:5000
   - Admin panel: http://localhost:5000/admin
   - API docs: http://localhost:5000/api

## 🐳 Docker Deployment

### Development with Docker
```bash
docker-compose up --build
```

### Production Deployment
1. **Configure environment variables**:
   ```bash
   cp .env.example .env.production
   # Edit .env.production with production values
   ```

2. **Deploy with Docker Compose**:
   ```bash
   docker-compose -f docker-compose.yml --env-file .env.production up -d
   ```

## 📁 Project Structure

```
ld-metrics-translator/
├── app/                     # Application package
│   ├── __init__.py         # Flask app factory
│   ├── models.py           # Database models
│   ├── routes.py           # Main routes
│   ├── api.py              # API endpoints
│   └── admin.py            # Admin interface
├── templates/              # Jinja2 templates
│   ├── base.html           # Base template
│   ├── index.html          # Homepage
│   ├── admin/              # Admin templates
│   └── errors/             # Error pages
├── static/                 # Static assets
│   ├── css/                # Stylesheets
│   ├── js/                 # JavaScript
│   └── images/             # Images
├── tests/                  # Test suite
├── scripts/                # Utility scripts
├── docs/                   # Documentation
├── logs/                   # Application logs
├── instance/               # Instance-specific files
├── config.py               # Configuration
├── run.py                  # Application entry point
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose setup
├── nginx.conf              # Nginx configuration
└── Makefile                # Development commands
```

## 🔧 Configuration

### Environment Variables

Key configuration options (see `.env.example` for complete list):

```bash
# Application
FLASK_ENV=production
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=postgresql://user:pass@localhost/ldmetrics

# Security
SESSION_COOKIE_SECURE=true

# Monitoring
SENTRY_DSN=your-sentry-dsn

# Email (for error notifications)
MAIL_SERVER=smtp.gmail.com
MAIL_USERNAME=your-email@example.com
```

## 🧪 Testing

### Run Tests
```bash
# All tests
make test

# With coverage
make test-coverage

# Specific test file
pytest tests/test_api.py -v

# Performance tests
make test-performance
```

### Test Coverage
The project maintains 95%+ test coverage across:
- Unit tests for models and utilities
- Integration tests for API endpoints
- End-to-end tests for user workflows
- Performance and security tests

## 📊 Monitoring and Logging

### Health Checks
- **Endpoint**: `/api/health`
- **Monitors**: Database connectivity, system status
- **Used by**: Load balancers, monitoring systems

### Logging
- **Development**: Console logging with DEBUG level
- **Production**: File rotation with WARNING+ levels
- **Error tracking**: Sentry integration for production

### Metrics
- Application performance metrics
- Database query performance
- User interaction analytics
- Error rates and response times

## 🔒 Security

### Security Features
- CSRF protection on all forms
- Secure session management
- SQL injection prevention
- XSS protection headers
- Rate limiting on API endpoints
- Input validation and sanitization

### Security Testing
```bash
# Security scan
make security-scan

# Dependency vulnerability check
make security-deps
```

## 🚀 Deployment

### Production Checklist

- [ ] Set `FLASK_ENV=production`
- [ ] Generate strong `SECRET_KEY`
- [ ] Configure production database
- [ ] Set up SSL certificates
- [ ] Configure email notifications
- [ ] Set up monitoring (Sentry)
- [ ] Configure backup procedures
- [ ] Test health check endpoints
- [ ] Verify security headers
- [ ] Load test the application

### Deployment Options

1. **Docker Compose** (Recommended)
2. **Kubernetes** (See `k8s/` directory)
3. **Traditional server** (See deployment docs)
4. **Cloud platforms** (AWS, GCP, Azure)

## 📚 API Documentation

### Core Endpoints

```bash
# Get all metrics
GET /api/metrics

# Search metrics
GET /api/metrics/search?q=engagement

# Get L&D outcomes
GET /api/outcomes

# Get metric types
GET /api/types

# Health check
GET /api/health
```

See [API Documentation](docs/api.md) for complete details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

See [Contributing Guide](docs/contributing.md) for detailed guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/your-org/ld-metrics-translator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/ld-metrics-translator/discussions)
- **Email**: support@ldmetrics.com

## 🏆 Acknowledgments

- L&D professionals who provided domain expertise
- Open source community for excellent tools
- Beta testers for valuable feedback

---

**Built with ❤️ for the L&D community**
