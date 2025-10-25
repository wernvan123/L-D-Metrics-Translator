from flask import Flask, request, make_response, session
import os
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
from config import config

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()


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
