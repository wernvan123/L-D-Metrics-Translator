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

### Reports API

The application exposes lightweight Reports endpoints to support the Reports list, single report view and comparison UI. In local development, the dev server in `app.py` serves safe SQLite-backed fallbacks under the same paths, returning empty results when no local DB is available. In the full backend, these endpoints are provided by the Flask package in `ld-metrics-translator/`.

### Generated PDF reports (stored path vs download name)

Dynamic reports are generated as PDFs and saved to disk, and also downloaded by users through HTTP endpoints.

- Stored path (`DynamicReport.pdf_path`)
  - This is the filesystem path where the generated PDF is persisted on disk.
  - Canonical location: `ld-metrics-translator/static/reports/<client_slug>/<engagement_slug>/...`

- Download name (`Content-Disposition` filename)
  - This is the user-facing filename suggested by the browser download prompt.
  - The backend stamps the download name with the active workspace prefix (client / engagement / session) for traceability.

Stored filename policy (dynamic reports):

- Stored PDFs are written using a title-based name that is always unique and traceable:
  - `<workspace_stamp>__<safe_title>__r<report_id>_<timestamp>.pdf`
  - Example: `monkey_river__6_week_diagnostic_sprint__s17723507__development_planx__r20_20260301_093855.pdf`

Legacy directory consolidation:

- Older builds stored PDFs under `ld-metrics-translator/app/static/reports/`.
- On startup, the backend attempts a best-effort consolidation:
  - Move legacy PDFs into: `ld-metrics-translator/static/reports/_legacy/`
  - Repoint any matching `DynamicReport.pdf_path` records to the new `_legacy` location.
  - This is intended to avoid broken downloads while keeping the canonical storage under `static/reports/`.

Endpoints:

- GET `/api/reports`
  - Description: Return a recent list of generated reports.
  - Response: `{ "reports": [ReportSummary...], "count": <int> }`
  - ReportSummary fields:
    - `id: int`
    - `title: str`
    - `generation_status: str` — one of `completed`, `in_progress`, `queued`, `failed` (UI maps to status badges)
    - `created_date: str` — creation timestamp (e.g. `YYYY-MM-DD HH:MM:SS`)
    - `generated_date: str|null` — set when `generation_status == completed`

- GET `/api/reports/<id>`
  - Description: Return a single report record.
  - Query params:
    - `include=content` — when present, include `content` or `content_html` fields if available
  - Response (200): `{ "report": ReportDetail }` or (404) `{ "error": "not found" }`
  - ReportDetail fields (superset of summary):
    - `id, title, generation_status, created_date, generated_date`
    - `content: object|string|null` — raw JSON/text content
    - `content_html: string|null` — optional pre-rendered HTML
    - `meta: object|null` — optional metadata (e.g. `meta.role_profile.name`)

Status meanings:

- `completed`: Report generation finished; `generated_date` populated.
- `in_progress` or `queued`: Generation in progress; `generated_date` may be null.
- `failed`: Generation failed; UI shows an error badge.

Date fields:

- `created_date`: When the report was first created.
- `generated_date`: When generation completed (if applicable).

Notes for dev server behavior (see `app.py`):

- `GET /api/reports` tries to read from `dynamic_reports` in `ld-metrics-translator/app.db` and gracefully falls back to an empty list.
- `GET /api/reports/<id>` returns 404 if the table or record is missing; when `?include=content` is passed, `content` is included if present in the table.

### Roles API

The Roles API supports CRUD operations for role profiles as well as selection and competency target management. In production, these endpoints require admin authentication (e.g., API key headers). Local dev stubs exist in `app.py` to exercise the UI:

Endpoints (dev stubs):

- GET `/api/roles`
  - Description: List role profiles.
  - Response: `{ "roles": [ { id, name, department, is_active, created_date }... ], "count": <int> }`

- POST `/api/roles` (admin required in real backend)
  - Description: Create a role profile.
  - Body: `{ name: str, department?: str, is_active?: bool }`
  - Response: `{ "role": { id, name, department, is_active, ... } }`

- GET `/api/roles/<id>`
  - Description: Get a single role profile.
  - Response: `{ "role": {...} }`

- PATCH `/api/roles/<id>` (admin required in real backend)
  - Description: Update a role profile.
  - Body: Partial fields (e.g., `{ name: "QA Engineer II" }`).
  - Response: `{ "role": {...} }`

- DELETE `/api/roles/<id>` (admin required in real backend)
  - Description: Delete/deactivate a role profile.
  - Response: `{ "ok": true }` or `{ "deleted": true }`

- GET `/api/roles/select`
  - Description: Retrieve the session-selected role id for the current user session.
  - Response: `{ "selected_role_profile_id": int|null }`

- POST `/api/roles/select`
  - Description: Set or clear the session-selected role id.
  - Body: `{ role_profile_id: int }` (or null/0 to clear)
  - Response: `{ "ok": true, "selected_role_profile_id": int|null }`

- GET `/api/roles/<id>/targets`
  - Description: Get competency targets for a role profile.
  - Response: `{ "targets": [ { competency_id, target_level, weight, competency_name? }... ], "count": <int> }`

- POST `/api/roles/<id>/targets` (admin required in real backend)
  - Description: Upsert competency targets for a role profile.
  - Body: `{ targets: [ { competency_id: int, target_level: int (0..5), weight?: number }... ] }`
  - Response: `{ "ok": true }` or created resource details

Admin requirements:

- In the real backend, `POST`, `PATCH`, and `DELETE` operations typically require admin authorization, e.g. an `X-API-Key` header associated with an active admin user. The tests (see `tests/test_roles_api.py`) demonstrate usage via `auth_headers`.

## Role Architect (Admin) Workflow

This feature allows HR/admins to create and manage Role Profiles (KSAOs) and connect them to Diagnostics and downstream planning.

### Admin entry points

- GET `/admin/roles` — Role Profile Library. Uses template `templates/roles_list.html` with `is_admin=True` to enable create/edit affordances.
- GET `/admin/roles/new` — Role Profile Wizard. Uses `templates/role_wizard.html` with `is_admin=True`.

In development (top-level `app.py`), lightweight routes exist to ensure these pages work even without the full Flask package loaded.

### Public entry points (auto-redirect for admins)

- GET `/roles` and `/roles/new` render the same templates for non-admin viewers with actions disabled.
- If the session indicates an admin is logged in, these public routes automatically redirect to the equivalent admin routes.

### Wizard behavior

- Multi-step: Basics → Knowledge → Skills → Abilities → Others → Targets → Review & Save.
- On Save:
  1. Create role `POST /api/roles` (if new) or update `PATCH /api/roles/<id>`.
  2. Bulk replace KSAOs `POST /api/roles/<id>/ksaos`.
  3. Bulk replace competency targets `POST /api/roles/<id>/targets`.
- Redirects:
  - If launched from `/admin/roles/new`, redirect to `/admin/roles?saved=1` so the Admin Library flashes a success message.
  - If launched from `/roles/new` (public), redirect to `/roles`.

### Flash messages

- Server-side flashes are rendered in `templates/base.html` via `get_flashed_messages()`.
- `/admin/roles` flashes “Role Profile saved successfully!” when `?saved=1` is present (set by the wizard on admin path).

### Diagnostics integration

- The Diagnostics page (`templates/diagnostics.html`) includes a "Role Profile" dropdown loaded from `GET /api/roles`.
- Selection is stored via `POST /api/roles/select` and restored using `GET /api/roles/select` (session-scoped).

### Seeding demo roles

- Use `scripts/seed_demo_roles.py` to insert demo roles with basic KSAOs into `ld-metrics-translator/app.db`.

```bash
python scripts/seed_demo_roles.py
```

### Dev login and route discovery

- Dev server provides a simplified admin login at `/admin/login` (no Flask-WTF dependencies). On successful POST, it sets admin flags in session and takes you to `/admin/roles`.
- To list key routes quickly, use `GET /api/routes_summary` (dev-only convenience).

### Dev caching guidance (templates/JS/CSS)

During development, browser caching can lead to stale templates and static assets. We employ two complementary strategies:

- Flask config in `app.py` sets `TEMPLATES_AUTO_RELOAD=True` and sends `Cache-Control: no-store` headers in debug mode.
- We append a version query parameter when referencing static assets from templates, e.g.:

  - `report_view.html` loads: `{{ url_for('static', filename='js/report-view.js') }}?v=20250915`
  - `reports_compare.html` loads: `{{ url_for('static', filename='js/reports.js') }}?v=20250915`
  - `reports_v2.html` loads: `{{ url_for('static', filename='js/reports-list.js') }}?v=20250916`

Best practice: When you change a static file (JS/CSS) and need to hard-refresh in dev or a demo environment, bump the `?v=` value in the template to invalidate caches.

### Seed demo data for Reports and UI verification

To quickly populate local demo data for the Reports UI, use the seeding script:

1. Ensure you are at the repository root and Python can write to `ld-metrics-translator/app.db`.
2. Run:

   ```bash
   python scripts/seed_demo_reports.py
   ```

   This will create tables `report_templates` and `dynamic_reports` if absent and insert three demo reports with realistic fields (`created_date`, `generated_date`, `generation_status`, etc.).

3. Start the dev server (e.g., via `run_dev.bat` or `python app.py`).

4. UI verification steps:

   - Reports list: Navigate to `/reports`. You should see demo rows with status badges and a working "Compare Reports" button enabling only when exactly two checkboxes are selected.
   - Single report view: Click "View" on a row to open `/report/<id>`. Page `report_view.html` initializes `report-view.js` which calls `GET /api/reports/<id>?include=content`. Verify the title, timestamps, and content rendering (raw JSON or `content_html` if present). Console should be clean of errors.
   - Compare two reports: From `/reports`, select two items and click "Compare Reports". This navigates to `/reports/compare?a=<idA>&b=<idB>`, loading `reports_compare.html` and `reports.js`. Each side loads its report, and the page shows a synthesized summary.

Troubleshooting:

- If the Reports list shows "No reports yet.", confirm the SQLite database path `ld-metrics-translator/app.db` exists and the `dynamic_reports` table contains rows (re-run the seed script if needed).
- If single report view shows a fallback message, verify the record exists with `GET /api/reports/<id>`.


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

#### Dev server port (8080 vs 5000)

- When you run the app via `python app.py` (used by `run_dev.bat` and `run_prod_parity.bat`), it binds to port 8080 by default, so the site will be at:
  - http://localhost:8080

- If you instead run via Flask CLI (`flask run`), Flask defaults to port 5000 unless you specify otherwise, so the site will be at:
  - http://localhost:5000

- To choose a port when using Flask CLI:
  - One‑off: `flask run --port 8080`
  - Or set an env var: `set FLASK_RUN_PORT=8080` (Windows) or `export FLASK_RUN_PORT=8080` (bash/zsh)

- To change the port for `python app.py`, update the `app.run(..., port=8080)` line in `app.py` to your preferred port.

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

## API Development

### RESTful Design Principles

The API follows REST conventions:

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

## Dependency Maintenance Rule

Whenever code changes add, remove, upgrade, or rely on any package, tool, runtime, framework feature, build step, or external integration, also check whether related dependency/config files need updating and update them if needed. This includes requirements.txt, pyproject.toml, package.json, lockfiles, Pipfile, poetry.lock, .env.example, deployment/build config files, and README/setup instructions. Keep dependency declarations accurate and minimal, do not add unused dependencies, remove obsolete dependencies when safe, follow the repository's authoritative dependency file and existing versioning style, create an appropriate dependency file if none exists but one is clearly needed, and mention dependency/config updates in the final summary. Before finishing any coding task, verify whether dependency/config/runtime files should also be updated.