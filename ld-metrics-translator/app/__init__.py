from flask import Flask, request, make_response, session
import json
import os
import shutil
import sqlalchemy as sa
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
from config import config

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()


def _ensure_dynamic_reports_workspace_columns(app: Flask) -> None:
    try:
        engine = db.engine
        insp = sa.inspect(engine)
        if 'dynamic_reports' not in insp.get_table_names():
            return

        cols = {c.get('name') for c in insp.get_columns('dynamic_reports')}
        ddl: list[str] = []
        if 'client_company_id' not in cols:
            ddl.append('ALTER TABLE dynamic_reports ADD COLUMN client_company_id INTEGER')
        if 'client_engagement_id' not in cols:
            ddl.append('ALTER TABLE dynamic_reports ADD COLUMN client_engagement_id INTEGER')

        if ddl:
            with engine.begin() as conn:
                for stmt in ddl:
                    conn.execute(sa.text(stmt))

        # Best-effort indexes (SQLite supports IF NOT EXISTS; other DBs may not)
        with engine.begin() as conn:
            try:
                conn.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_dynamic_reports_client_company_id ON dynamic_reports (client_company_id)'))
            except Exception:
                pass
            try:
                conn.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_dynamic_reports_client_engagement_id ON dynamic_reports (client_engagement_id)'))
            except Exception:
                pass
    except Exception:
        try:
            app.logger.exception('Failed to ensure dynamic_reports workspace columns')
        except Exception:
            pass


def _backfill_dynamic_reports_workspace_ids(app: Flask) -> None:
    try:
        from app.models import DynamicReport, ClientCompany, ClientEngagement
        from app.workspace_stamp import workspace_from_pdf_path, safe_component

        # Only touch rows that are missing workspace IDs
        rows = (
            DynamicReport.query
            .filter(
                sa.or_(
                    DynamicReport.client_company_id.is_(None),
                    DynamicReport.client_engagement_id.is_(None),
                )
            )
            .all()
        )
        if not rows:
            return

        engagements_by_client: dict[int, list[ClientEngagement]] = {}

        def _resolve_client_id(client_slug: str) -> int | None:
            try:
                if not client_slug:
                    return None
                # First preference: exact match on stored slug
                cc = ClientCompany.query.filter(ClientCompany.slug == client_slug).first()
                if cc:
                    return int(cc.id)

                # Fallback: normalized match (handles '-' vs '_' etc.)
                for c in ClientCompany.query.all():
                    stored = safe_component(getattr(c, 'slug', None) or getattr(c, 'name', None) or '', default='')
                    if stored and stored == client_slug:
                        return int(c.id)
            except Exception:
                return None
            return None

        def _resolve_engagement_id(client_id: int, engagement_slug: str) -> int | None:
            try:
                if not client_id or not engagement_slug:
                    return None
                if client_id not in engagements_by_client:
                    engagements_by_client[client_id] = (
                        ClientEngagement.query
                        .filter(ClientEngagement.client_company_id == int(client_id))
                        .all()
                    )
                for e in engagements_by_client.get(client_id) or []:
                    if safe_component(getattr(e, 'name', None) or '', default='') == engagement_slug:
                        return int(e.id)
            except Exception:
                return None
            return None

        changed = False
        for r in rows:
            try:
                if r.client_company_id is not None and r.client_engagement_id is not None:
                    continue

                ctx = {}
                try:
                    if r.generation_context:
                        ctx = json.loads(r.generation_context) if isinstance(r.generation_context, str) else (r.generation_context or {})
                        if not isinstance(ctx, dict):
                            ctx = {}
                except Exception:
                    ctx = {}

                # First preference: explicit IDs in context
                ccid = None
                ceid = None
                try:
                    if ctx.get('client_company_id') is not None:
                        ccid = int(ctx.get('client_company_id'))
                except Exception:
                    ccid = None
                try:
                    if ctx.get('client_engagement_id') is not None:
                        ceid = int(ctx.get('client_engagement_id'))
                except Exception:
                    ceid = None

                # Fallback: resolve from slugs
                if not ccid or not ceid:
                    slug_info = {}
                    try:
                        slug_info = {
                            'client_slug': ctx.get('client_slug'),
                            'engagement_slug': ctx.get('engagement_slug'),
                        }
                    except Exception:
                        slug_info = {}

                    if not (slug_info.get('client_slug') and slug_info.get('engagement_slug')):
                        slug_info = workspace_from_pdf_path(getattr(r, 'pdf_path', None)) or slug_info

                    client_slug = safe_component(slug_info.get('client_slug') or '', default='')
                    engagement_slug = safe_component(slug_info.get('engagement_slug') or '', default='')
                    if client_slug and not ccid:
                        ccid = _resolve_client_id(client_slug)
                    if ccid and engagement_slug and not ceid:
                        ceid = _resolve_engagement_id(ccid, engagement_slug)

                if ccid and ceid:
                    r.client_company_id = int(ccid)
                    r.client_engagement_id = int(ceid)
                    changed = True
            except Exception:
                continue

        if changed:
            db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        try:
            app.logger.exception('Failed to backfill dynamic_reports workspace IDs')
        except Exception:
            pass


def _consolidate_legacy_reports(app: Flask):
    try:
        legacy_root = os.path.join(os.path.dirname(__file__), 'static', 'reports')
        if not os.path.isdir(legacy_root):
            return

        canonical_root = os.path.join(app.static_folder, 'reports')
        legacy_target = os.path.join(canonical_root, '_legacy')
        os.makedirs(legacy_target, exist_ok=True)

        moved: dict[str, str] = {}
        legacy_root_norm = os.path.normpath(legacy_root)

        for root, _dirs, files in os.walk(legacy_root):
            for name in files:
                if not str(name).lower().endswith('.pdf'):
                    continue
                src = os.path.join(root, name)
                if not os.path.isfile(src):
                    continue

                rel_dir = os.path.relpath(root, legacy_root)
                dst_dir = legacy_target if rel_dir in ('.', '') else os.path.join(legacy_target, rel_dir)
                os.makedirs(dst_dir, exist_ok=True)

                dst = os.path.join(dst_dir, name)
                if os.path.exists(dst):
                    base, ext = os.path.splitext(name)
                    i = 2
                    while True:
                        candidate = os.path.join(dst_dir, f"{base}_{i}{ext}")
                        if not os.path.exists(candidate):
                            dst = candidate
                            break
                        i += 1

                try:
                    shutil.move(src, dst)
                    moved[os.path.normpath(src)] = os.path.normpath(dst)
                except Exception:
                    continue

        try:
            from app.models import DynamicReport
        except Exception:
            return

        changed = False
        for r in DynamicReport.query.filter(DynamicReport.pdf_path.isnot(None)).all():
            p = r.pdf_path
            if not p:
                continue
            p_norm = os.path.normpath(p)
            if p_norm in moved:
                r.pdf_path = moved[p_norm]
                changed = True
                continue

            try:
                common = os.path.commonpath([legacy_root_norm, p_norm])
            except Exception:
                common = None
            if common and common == legacy_root_norm:
                rel = os.path.relpath(p_norm, legacy_root_norm)
                candidate = os.path.normpath(os.path.join(legacy_target, rel))
                if os.path.exists(candidate):
                    r.pdf_path = candidate
                    changed = True

        if changed:
            db.session.commit()
    except Exception:
        try:
            app.logger.exception('Failed to consolidate legacy reports directory')
        except Exception:
            pass


def create_app(config_name='default'):
    """Create and configure Flask application."""
    import os
    app = Flask(__name__, 
                template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
                static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'))
    
    # Load configuration
    # Tests may pass a dict of overrides as config_name
    if isinstance(config_name, dict):
        # Apply provided overrides directly
        app.config.update(config_name)
    else:
        config_obj = config[config_name]
        app.config.from_object(config_obj)
        # Some config objects may not have init_app
        if hasattr(config_obj, 'init_app'):
            config_obj.init_app(app)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Import blueprints
    from app.routes import main
    from app.api import api
    from app.admin import admin
    from app.pdf_routes import pdf_bp
    from app.context_api import context_api
    
    # Initialize CSRF protection but don't enable it yet
    csrf = CSRFProtect()
    
    # Register blueprints
    app.register_blueprint(main)
    # The 'api' blueprint already defines url_prefix='/api' in app/api.py
    app.register_blueprint(api)
    app.register_blueprint(admin)
    app.register_blueprint(pdf_bp)
    app.register_blueprint(context_api)
    
    # Configure CORS for API endpoints
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Configure CSRF protection (respect existing setting if provided)
    if 'WTF_CSRF_ENABLED' not in app.config:
        app.config['WTF_CSRF_ENABLED'] = True
    if 'WTF_CSRF_TIME_LIMIT' not in app.config:
        app.config['WTF_CSRF_TIME_LIMIT'] = None
    if 'WTF_CSRF_METHODS' not in app.config:
        app.config['WTF_CSRF_METHODS'] = ['POST', 'PUT', 'PATCH', 'DELETE']
    
    # Initialize CSRF protection
    csrf.init_app(app)
    
    # Exempt API routes from CSRF protection
    csrf.exempt(api)
    csrf.exempt(context_api)
    csrf.exempt(pdf_bp)
    
    # Initialize error tracking (Sentry)
    if app.config.get('SENTRY_DSN'):
        try:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
            
            sentry_sdk.init(
                dsn=app.config['SENTRY_DSN'],
                integrations=[
                    FlaskIntegration(transaction_style='endpoint'),
                    SqlalchemyIntegration(),
                ],
                traces_sample_rate=0.1,
                environment=config_name
            )
        except ImportError:
            app.logger.warning('Sentry SDK not installed, error tracking disabled')
    
    # Register error handlers
    register_error_handlers(app)

    # Expose feature flags to all templates
    @app.context_processor
    def inject_feature_flags():
        cfg = app.config
        return {
            'UI_TABS_V2': bool(cfg.get('UI_TABS_V2')),
            'HOME_HERO_V2': bool(cfg.get('HOME_HERO_V2')),
            'DRIVER_CARDS_V1': bool(cfg.get('DRIVER_CARDS_V1')),
            'ENABLE_EVENT_KB': bool(cfg.get('ENABLE_EVENT_KB')),
            'is_admin': bool(session.get('admin_user_id')),
        }
    
    # Ensure DB connections are cleaned up (important for Windows file locks)
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        try:
            db.session.remove()
        finally:
            # Dispose engine to close all pooled connections
            try:
                # Avoid disposing in-memory SQLite engine as it wipes the DB
                uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
                if not (uri.startswith('sqlite:///:memory:') or uri == 'sqlite://'):
                    db.engine.dispose()
            except Exception:
                pass
    
    # Create database tables
    with app.app_context():
        db.create_all()
        _ensure_dynamic_reports_workspace_columns(app)
        _consolidate_legacy_reports(app)
        _backfill_dynamic_reports_workspace_ids(app)
    
    return app


def register_error_handlers(app):
    """Register application error handlers."""
    
    @app.errorhandler(404)
    def not_found_error(error):
        from flask import render_template, request, jsonify
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Resource not found'}), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template, request, jsonify
        db.session.rollback()
        app.logger.error(f'Server Error: {error}')
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        from flask import render_template, request, jsonify
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Access forbidden'}), 403
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        from flask import jsonify, request
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Rate limit exceeded', 'retry_after': str(e.retry_after)}), 429
        return render_template('errors/429.html', retry_after=e.retry_after), 429

# Expose a default Flask app instance for convenience in non-test environments
# During tests, set env var DISABLE_DEFAULT_FLASK_APP=1 to prevent double registration
if not os.environ.get('DISABLE_DEFAULT_FLASK_APP'):
    app = create_app()
