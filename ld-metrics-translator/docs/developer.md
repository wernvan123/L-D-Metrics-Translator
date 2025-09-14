# Developer Documentation

This guide provides comprehensive information for developers working on the L&D Metrics Translator application.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Development Setup](#development-setup)
3. [Code Structure](#code-structure)
4. [Database Design](#database-design)
5. [API Development](#api-development)
6. [Frontend Development](#frontend-development)
7. [Testing](#testing)
8. [Deployment](#deployment)
9. [Contributing](#contributing)

## Architecture Overview

### Technology Stack

**Backend:**
- **Framework**: Flask 2.3+ with Blueprints
- **Database**: SQLAlchemy ORM with PostgreSQL/SQLite
- **Migration**: Flask-Migrate (Alembic)
- **Authentication**: Flask-WTF with CSRF protection
- **API**: RESTful endpoints with JSON responses

**Frontend:**
- **Templates**: Jinja2 templating engine
- **Styling**: CSS3 with custom variables
- **JavaScript**: Vanilla ES6+ with modern features
- **Responsive**: Mobile-first design approach

**Infrastructure:**
- **Web Server**: Gunicorn with Nginx reverse proxy
- **Caching**: Redis for session storage and rate limiting
- **Monitoring**: Sentry for error tracking
- **Containerization**: Docker with multi-stage builds

### Application Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │    │     Nginx       │    │   Flask App     │
│                 │◄──►│  (Reverse Proxy)│◄──►│   (Gunicorn)    │
│  (JavaScript)   │    │   (Static Files)│    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                               ┌─────────────────┐
                                               │   PostgreSQL    │
                                               │   (Database)    │
                                               └─────────────────┘
                                                        │
                                               ┌─────────────────┐
                                               │     Redis       │
                                               │  (Cache/Sessions)│
                                               └─────────────────┘
```

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 16+ (for frontend tooling)
- PostgreSQL 13+ (or SQLite for development)
- Redis 6+ (optional for development)
- Git

### Local Development Environment

1. **Clone Repository:**
   ```bash
   git clone https://github.com/your-org/ld-metrics-translator.git
   cd ld-metrics-translator
   ```

2. **Python Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows
   pip install -r requirements.txt
   ```

3. **Environment Configuration:**
   ```bash
   cp .env.example .env
   # Edit .env with development settings
   ```

4. **Database Setup:**
   ```bash
   python init_db.py
   python seed_database.py
   python setup_admin.py
   ```

5. **Run Development Server:**
   ```bash
   python run.py
   ```

### Development Tools

**Code Quality:**
```bash
# Linting
flake8 app/ tests/
black app/ tests/
isort app/ tests/

# Type checking
mypy app/

# Security scanning
bandit -r app/
```

**Testing:**
```bash
# Unit tests
pytest tests/

# Coverage
pytest --cov=app tests/

# Performance tests
locust -f locustfile.py
```

## Code Structure

### Project Organization

```
ld-metrics-translator/
├── app/                    # Main application package
│   ├── __init__.py        # Flask app factory
│   ├── models.py          # SQLAlchemy models
│   ├── routes.py          # Main application routes
│   ├── api.py             # API endpoints
│   └── admin.py           # Admin interface
├── templates/             # Jinja2 templates
│   ├── base.html         # Base template
│   ├── index.html        # Homepage
│   ├── admin/            # Admin templates
│   └── errors/           # Error pages
├── static/               # Static assets
│   ├── css/             # Stylesheets
│   ├── js/              # JavaScript files
│   └── images/          # Images and icons
├── tests/               # Test suite
│   ├── conftest.py      # Test configuration
│   ├── test_models.py   # Model tests
│   ├── test_api.py      # API tests
│   └── test_routes.py   # Route tests
├── scripts/             # Utility scripts
├── docs/               # Documentation
├── config.py           # Configuration classes
└── run.py             # Application entry point
```

### Flask Application Factory

The application uses the factory pattern for better testability and configuration management:

```python
# app/__init__.py
def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    
    # Register blueprints
    from app.routes import main
    from app.api import api
    from app.admin import admin
    
    app.register_blueprint(main)
    app.register_blueprint(api)
    app.register_blueprint(admin)
    
    return app
```

### Configuration Management

Environment-specific configurations are managed through classes:

```python
# config.py
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    # ... other base configurations

class DevelopmentConfig(Config):
    DEBUG = True
    # ... development-specific settings

class ProductionConfig(Config):
    DEBUG = False
    # ... production-specific settings
```

## Database Design

### Entity Relationship Diagram

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   LDOutcome     │    │     Metric      │    │   MetricType    │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ id (PK)         │◄──►│ id (PK)         │◄──►│ id (PK)         │
│ name            │    │ name            │    │ name            │
│ description     │    │ description     │    │ description     │
│ created_at      │    │ example         │    │ created_at      │
│ updated_at      │    │ ld_outcome_id   │    │ updated_at      │
└─────────────────┘    │ metric_type_id  │    └─────────────────┘
                       │ created_at      │
                       │ updated_at      │
                       └─────────────────┘
                                │
                       ┌─────────────────┐
                       │   AdminUser     │
                       ├─────────────────┤
                       │ id (PK)         │
                       │ username        │
                       │ email           │
                       │ password_hash   │
                       │ is_active       │
                       │ created_at      │
                       │ last_login      │
                       └─────────────────┘
```

### Model Definitions

**Metric Model:**
```python
class Metric(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    example = db.Column(db.Text)
    ld_outcome_id = db.Column(db.Integer, db.ForeignKey('ld_outcome.id'))
    metric_type_id = db.Column(db.Integer, db.ForeignKey('metric_type.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ld_outcome = db.relationship('LDOutcome', backref='metrics')
    metric_type = db.relationship('MetricType', backref='metrics')
```

### Database Migrations

Using Flask-Migrate for schema management:

```bash
# Create migration
flask db migrate -m "Description of changes"

# Apply migration
flask db upgrade

# Downgrade migration
flask db downgrade
```

### Indexing Strategy

Key indexes for performance:

```sql
-- Frequently queried columns
CREATE INDEX idx_metrics_outcome ON metrics(ld_outcome_id);
CREATE INDEX idx_metrics_type ON metrics(metric_type_id);
CREATE INDEX idx_metrics_name ON metrics(name);

-- Full-text search (PostgreSQL)
CREATE INDEX idx_metrics_search ON metrics USING gin(to_tsvector('english', name || ' ' || description || ' ' || example));
```

## API Development

### RESTful Design Principles

The API follows REST conventions:

- **GET**: Retrieve resources
- **POST**: Create new resources
- **PUT**: Update entire resources
- **PATCH**: Partial resource updates
- **DELETE**: Remove resources

### API Endpoints Structure

```python
# app/api.py
@api.route('/metrics', methods=['GET'])
def get_metrics():
    """Get all metrics with filtering and pagination."""
    
@api.route('/metrics/<int:id>', methods=['GET'])
def get_metric(id):
    """Get specific metric by ID."""
    
@api.route('/metrics/search', methods=['GET'])
def search_metrics():
    """Full-text search across metrics."""
```

### Response Format Standardization

Consistent JSON response structure:

```python
def api_response(data=None, error=None, status_code=200, **kwargs):
    """Standardized API response format."""
    response = {
        'timestamp': datetime.utcnow().isoformat(),
        'status': 'success' if error is None else 'error'
    }
    
    if data is not None:
        response['data'] = data
    if error is not None:
        response['error'] = error
    
    response.update(kwargs)
    return jsonify(response), status_code
```

### Error Handling

Comprehensive error handling with appropriate HTTP status codes:

```python
@api.errorhandler(404)
def not_found_error(error):
    return api_response(
        error='Resource not found',
        status_code=404
    )

@api.errorhandler(ValidationError)
def validation_error(error):
    return api_response(
        error='Validation failed',
        details=error.messages,
        status_code=400
    )
```

### Rate Limiting

API rate limiting implementation:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)

@api.route('/metrics')
@limiter.limit("50 per minute")
def get_metrics():
    # Implementation
```

## Frontend Development

### Template Structure

Base template with blocks for extensibility:

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}L&D Metrics Translator{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    {% block extra_css %}{% endblock %}
</head>
<body>
    <nav class="navbar">
        <!-- Navigation content -->
    </nav>
    
    <main class="main-content">
        {% block content %}{% endblock %}
    </main>
    
    <script src="{{ url_for('static', filename='js/main.js') }}"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>
```

### CSS Architecture

Organized CSS with custom properties:

```css
/* static/css/style.css */
:root {
    --primary-color: #2c3e50;
    --secondary-color: #3498db;
    --success-color: #27ae60;
    --warning-color: #f39c12;
    --danger-color: #e74c3c;
    --text-color: #2c3e50;
    --text-muted: #7f8c8d;
    --background-color: #ffffff;
    --border-color: #bdc3c7;
}

/* Component-based organization */
.navbar { /* Navigation styles */ }
.card { /* Card component styles */ }
.btn { /* Button component styles */ }
.form { /* Form component styles */ }
```

### JavaScript Architecture

Modern ES6+ JavaScript with modules:

```javascript
// static/js/main.js
class MetricsApp {
    constructor() {
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadInitialData();
    }
    
    bindEvents() {
        document.addEventListener('DOMContentLoaded', () => {
            this.setupSearch();
            this.setupFilters();
        });
    }
    
    async loadInitialData() {
        try {
            const response = await fetch('/api/metrics');
            const data = await response.json();
            this.renderMetrics(data.data);
        } catch (error) {
            console.error('Failed to load metrics:', error);
        }
    }
}

// Initialize application
new MetricsApp();
```

### AJAX and API Integration

Fetch API for modern HTTP requests:

```javascript
class ApiClient {
    constructor(baseUrl = '/api') {
        this.baseUrl = baseUrl;
    }
    
    async get(endpoint, params = {}) {
        const url = new URL(`${this.baseUrl}${endpoint}`, window.location.origin);
        Object.keys(params).forEach(key => 
            url.searchParams.append(key, params[key])
        );
        
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return response.json();
    }
    
    async search(query, filters = {}) {
        return this.get('/metrics/search', { q: query, ...filters });
    }
}
```

## Testing

### Test Structure

Comprehensive test suite organization:

```
tests/
├── conftest.py          # Pytest configuration and fixtures
├── test_models.py       # Model unit tests
├── test_api.py          # API endpoint tests
├── test_routes.py       # Route integration tests
├── test_admin.py        # Admin functionality tests
└── test_performance.py  # Performance and load tests
```

### Test Configuration

```python
# tests/conftest.py
import pytest
from app import create_app, db
from app.models import Metric, LDOutcome, MetricType

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def sample_metric(app):
    outcome = LDOutcome(name='Test Outcome')
    metric_type = MetricType(name='Test Type')
    metric = Metric(
        name='Test Metric',
        description='Test description',
        ld_outcome=outcome,
        metric_type=metric_type
    )
    db.session.add_all([outcome, metric_type, metric])
    db.session.commit()
    return metric
```

### Unit Testing

Model and utility function tests:

```python
# tests/test_models.py
def test_metric_creation(app):
    """Test metric model creation and relationships."""
    with app.app_context():
        outcome = LDOutcome(name='Engagement')
        metric_type = MetricType(name='KPI')
        metric = Metric(
            name='Test Metric',
            description='Test description',
            ld_outcome=outcome,
            metric_type=metric_type
        )
        
        db.session.add_all([outcome, metric_type, metric])
        db.session.commit()
        
        assert metric.id is not None
        assert metric.ld_outcome.name == 'Engagement'
        assert metric.metric_type.name == 'KPI'
```

### API Testing

Endpoint functionality and response validation:

```python
# tests/test_api.py
def test_get_metrics(client, sample_metric):
    """Test metrics API endpoint."""
    response = client.get('/api/metrics')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'data' in data
    assert len(data['data']) > 0
    assert data['data'][0]['name'] == 'Test Metric'

def test_search_metrics(client, sample_metric):
    """Test metrics search functionality."""
    response = client.get('/api/metrics/search?q=Test')
    assert response.status_code == 200
    
    data = response.get_json()
    assert len(data['data']) > 0
```

### Integration Testing

End-to-end workflow testing:

```python
# tests/test_integration.py
def test_metric_workflow(client):
    """Test complete metric discovery workflow."""
    # Search for metrics
    response = client.get('/api/metrics/search?q=engagement')
    assert response.status_code == 200
    
    # Get specific metric
    metrics = response.get_json()['data']
    if metrics:
        metric_id = metrics[0]['id']
        response = client.get(f'/api/metrics/{metric_id}')
        assert response.status_code == 200
```

### Performance Testing

Load testing with Locust:

```python
# locustfile.py
from locust import HttpUser, task, between

class MetricsUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def view_metrics(self):
        self.client.get("/api/metrics")
    
    @task(2)
    def search_metrics(self):
        self.client.get("/api/metrics/search?q=engagement")
    
    @task(1)
    def view_homepage(self):
        self.client.get("/")
```

## Deployment

### Docker Configuration

Multi-stage Dockerfile for optimized builds:

```dockerfile
# Build stage
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Production stage
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]
```

### Environment Configuration

Production environment setup:

```bash
# .env.production
FLASK_ENV=production
SECRET_KEY=your-production-secret-key
DATABASE_URL=postgresql://user:pass@db:5432/ldmetrics
REDIS_URL=redis://redis:6379/0
SENTRY_DSN=your-sentry-dsn
```

### CI/CD Pipeline

GitHub Actions workflow:

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest --cov=app tests/
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Contributing

### Development Workflow

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/new-feature`
3. **Make changes** with appropriate tests
4. **Run test suite**: `pytest tests/`
5. **Check code quality**: `flake8 app/ tests/`
6. **Submit pull request** with detailed description

### Code Standards

**Python Style:**
- Follow PEP 8 guidelines
- Use Black for code formatting
- Maximum line length: 88 characters
- Use type hints where appropriate

**JavaScript Style:**
- Use ES6+ features
- Consistent indentation (2 spaces)
- Meaningful variable names
- Document complex functions

**Documentation:**
- Docstrings for all public functions
- Inline comments for complex logic
- Update documentation with changes
- Include examples in docstrings

### Pull Request Guidelines

**Requirements:**
- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
- [ ] Performance impact considered

**Review Process:**
1. Automated checks must pass
2. Code review by maintainer
3. Manual testing if needed
4. Merge after approval

### Issue Reporting

**Bug Reports:**
- Use the bug report template
- Include steps to reproduce
- Provide environment details
- Attach screenshots if relevant

**Feature Requests:**
- Describe the use case
- Explain expected behavior
- Consider implementation complexity
- Discuss with maintainers first

---

For additional development questions, consult the [API documentation](api.md) or reach out to the development team at dev@ldmetrics.com.
