import os
import logging
from datetime import timedelta
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    """Base configuration class."""
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-123'
    WTF_CSRF_TIME_LIMIT = None
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = os.environ.get('SQLALCHEMY_RECORD_QUERIES', 'False').lower() == 'true'
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'connect_args': {'timeout': 20} if 'sqlite' in os.environ.get('DATABASE_URL', '') else {}
    }
    
    # Application
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file upload
    JSONIFY_PRETTYPRINT_REGULAR = False
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', os.path.join(basedir, 'logs', 'app.log'))
    LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES', 10485760))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 5))
    
    # Performance
    SEND_FILE_MAX_AGE_DEFAULT = timedelta(hours=1)
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '100 per hour')
    
    # Monitoring
    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    ENABLE_METRICS = os.environ.get('ENABLE_METRICS', 'False').lower() == 'true'

    # Ollama integration
    OLLAMA_TIMEOUT = int(os.environ.get('OLLAMA_TIMEOUT', 120))
    OLLAMA_MAX_RETRIES = int(os.environ.get('OLLAMA_MAX_RETRIES', 1))
    OLLAMA_RETRY_BACKOFF = float(os.environ.get('OLLAMA_RETRY_BACKOFF', 2.0))

    # Feature Flags (non-invasive, default off)
    UI_TABS_V2 = os.environ.get('UI_TABS_V2', 'False').lower() == 'true'
    HOME_HERO_V2 = os.environ.get('HOME_HERO_V2', 'False').lower() == 'true'
    DRIVER_CARDS_V1 = os.environ.get('DRIVER_CARDS_V1', 'False').lower() == 'true'
    ENABLE_EVENT_KB = os.environ.get('ENABLE_EVENT_KB', 'False').lower() == 'true'
    
    @staticmethod
    def init_app(app):
        """Initialize application with configuration-specific settings."""
        # Ensure logs directory exists
        log_dir = os.path.dirname(Config.LOG_FILE)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    SQLALCHEMY_RECORD_QUERIES = True
    SESSION_COOKIE_SECURE = False
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        
        # Development-specific logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s %(levelname)s %(name)s: %(message)s'
        )


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SQLALCHEMY_RECORD_QUERIES = False
    LOG_LEVEL = 'WARNING'
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        
        # Production logging setup
        from logging.handlers import RotatingFileHandler, SMTPHandler
        import logging
        
        # File handler
        file_handler = RotatingFileHandler(
            Config.LOG_FILE,
            maxBytes=Config.LOG_MAX_BYTES,
            backupCount=Config.LOG_BACKUP_COUNT
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)
        
        # Email handler for critical errors
        mail_server = os.environ.get('MAIL_SERVER')
        if mail_server:
            auth = None
            if os.environ.get('MAIL_USERNAME') or os.environ.get('MAIL_PASSWORD'):
                auth = (os.environ.get('MAIL_USERNAME'), os.environ.get('MAIL_PASSWORD'))
            secure = None
            if os.environ.get('MAIL_USE_TLS'):
                secure = ()
            mail_handler = SMTPHandler(
                mailhost=(mail_server, int(os.environ.get('MAIL_PORT', 587))),
                fromaddr=os.environ.get('MAIL_FROM', 'noreply@ldmetrics.com'),
                toaddrs=os.environ.get('ADMINS', '').split(','),
                subject='L&D Metrics Translator Application Error',
                credentials=auth,
                secure=secure
            )
            mail_handler.setLevel(logging.ERROR)
            mail_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            app.logger.addHandler(mail_handler)
        
        app.logger.setLevel(logging.WARNING)
        app.logger.info('L&D Metrics Translator startup')


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False
    LOG_LEVEL = 'ERROR'
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        
        # Suppress logging during tests
        logging.disable(logging.CRITICAL)


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
