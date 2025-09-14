from datetime import datetime, timezone
from app import db
from sqlalchemy import event
from sqlalchemy.orm import validates
from werkzeug.security import generate_password_hash, check_password_hash


class LDOutcome(db.Model):
    """L&D Outcome categories (Engagement, Retention, etc.)."""
    __tablename__ = 'ld_outcomes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationship
    metrics = db.relationship('Metric', backref='ld_outcome', lazy='dynamic')
    
    @validates('name')
    def validate_name(self, key, name):
        """Validate L&D outcome name."""
        if not name or not name.strip():
            raise ValueError("L&D outcome name cannot be empty")
        if len(name.strip()) > 100:
            raise ValueError("L&D outcome name cannot exceed 100 characters")
        return name.strip().title()
    
    def __repr__(self):
        return f'<LDOutcome {self.name}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'metrics_count': self.metrics.count()
        }


class MetricType(db.Model):
    """Metric type categories (Operational KPI, Behavioral Metric, etc.)."""
    __tablename__ = 'metric_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationship
    metrics = db.relationship('Metric', backref='metric_type', lazy='dynamic')
    
    @validates('name')
    def validate_name(self, key, name):
        """Validate metric type name."""
        if not name or not name.strip():
            raise ValueError("Metric type name cannot be empty")
        if len(name.strip()) > 100:
            raise ValueError("Metric type name cannot exceed 100 characters")
        # Apply title case but preserve KPI capitalization
        result = name.strip().title()
        result = result.replace('Kpi', 'KPI')
        return result
    
    def __repr__(self):
        return f'<MetricType {self.name}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'metrics_count': self.metrics.count()
        }


class Metric(db.Model):
    """Individual metrics and concepts."""
    __tablename__ = 'metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    example = db.Column(db.Text)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Foreign keys
    ld_outcome_id = db.Column(db.Integer, db.ForeignKey('ld_outcomes.id'), nullable=False)
    metric_type_id = db.Column(db.Integer, db.ForeignKey('metric_types.id'), nullable=False)
    
    @validates('name')
    def validate_name(self, key, name):
        """Validate metric name."""
        if not name or not name.strip():
            raise ValueError("Metric name cannot be empty")
        if len(name.strip()) > 200:
            raise ValueError("Metric name cannot exceed 200 characters")
        return name.strip()
    
    @validates('description')
    def validate_description(self, key, description):
        """Validate metric description."""
        if not description or not description.strip():
            raise ValueError("Metric description cannot be empty")
        return description.strip()
    
    def __repr__(self):
        return f'<Metric {self.name}>'
    
    def to_dict(self):
        """Convert metric to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'example': self.example,
            'ld_outcome': self.ld_outcome.name if self.ld_outcome else None,
            'metric_type': self.metric_type.name if self.metric_type else None,
            'ld_outcome_id': self.ld_outcome_id,
            'metric_type_id': self.metric_type_id,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'updated_date': self.updated_date.isoformat() if self.updated_date else None
        }
    
    @classmethod
    def search(cls, query):
        """Search metrics by name, description, or example."""
        if not query:
            return cls.query
        
        search_term = f"%{query}%"
        return cls.query.filter(
            db.or_(
                cls.name.ilike(search_term),
                cls.description.ilike(search_term),
                cls.example.ilike(search_term)
            )
        )
    
    @classmethod
    def filter_by_outcome(cls, outcome_id):
        """Filter metrics by L&D outcome."""
        if not outcome_id:
            return cls.query
        return cls.query.filter_by(ld_outcome_id=outcome_id)
    
    @classmethod
    def filter_by_type(cls, type_id):
        """Filter metrics by metric type."""
        if not type_id:
            return cls.query
        return cls.query.filter_by(metric_type_id=type_id)


class AdminUser(db.Model):
    """Admin users for the administrative interface."""
    __tablename__ = 'admin_users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)
    
    # Relationship
    audit_logs = db.relationship('AuditLog', backref='admin_user', lazy='dynamic')
    
    def set_password(self, password):
        """Set password hash."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash."""
        return check_password_hash(self.password_hash, password)
    
    @validates('username')
    def validate_username(self, key, username):
        """Validate username."""
        if not username or not username.strip():
            raise ValueError("Username cannot be empty")
        if len(username.strip()) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if len(username.strip()) > 50:
            raise ValueError("Username cannot exceed 50 characters")
        return username.strip().lower()
    
    @validates('email')
    def validate_email(self, key, email):
        """Validate email."""
        if not email or not email.strip():
            raise ValueError("Email cannot be empty")
        if '@' not in email:
            raise ValueError("Invalid email format")
        return email.strip().lower()
    
    def __repr__(self):
        return f'<AdminUser {self.username}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class AuditLog(db.Model):
    """Audit log for tracking admin actions."""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    admin_user_id = db.Column(db.Integer, db.ForeignKey('admin_users.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    ip_address = db.Column(db.String(45))  # IPv6 compatible
    
    def __repr__(self):
        return f'<AuditLog {self.action} by {self.admin_user.username}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'admin_user_id': self.admin_user_id,
            'admin_username': self.admin_user.username if self.admin_user else 'Unknown',
            'action': self.action,
            'details': self.details,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'ip_address': self.ip_address
        }


class Experience(db.Model):
    """Employee experiences for improving recommendations."""
    __tablename__ = 'experiences'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(100))
    employee_name = db.Column(db.String(200))
    context = db.Column(db.Text, nullable=False)
    experience_description = db.Column(db.Text, nullable=False)
    outcomes = db.Column(db.Text)
    keywords = db.Column(db.Text)  # Extracted keywords for matching
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('admin_users.id'))
    
    # Relationships
    metrics = db.relationship('Metric', secondary='experience_metrics', backref='experiences')
    
    @validates('context', 'experience_description')
    def validate_required_fields(self, key, value):
        """Validate required text fields."""
        if not value or not value.strip():
            raise ValueError(f"{key.replace('_', ' ').title()} cannot be empty")
        return value.strip()
    
    def __repr__(self):
        return f'<Experience {self.id}: {self.employee_name or self.employee_id}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'employee_name': self.employee_name,
            'context': self.context,
            'experience_description': self.experience_description,
            'outcomes': self.outcomes,
            'keywords': self.keywords,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'created_by': self.created_by,
            'metrics': [metric.name for metric in self.metrics]
        }


class Report(db.Model):
    """Generated reports with recommendations."""
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    context = db.Column(db.Text, nullable=False)
    selected_metrics = db.Column(db.Text, nullable=False)  # JSON string of metric IDs
    recommendations = db.Column(db.Text)
    pdf_path = db.Column(db.String(500))
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('admin_users.id'))
    
    # Relationships
    metrics = db.relationship('Metric', secondary='report_metrics', backref='reports')
    
    @validates('title', 'context')
    def validate_required_fields(self, key, value):
        """Validate required fields."""
        if not value or not value.strip():
            raise ValueError(f"{key.replace('_', ' ').title()} cannot be empty")
        return value.strip()
    
    def __repr__(self):
        return f'<Report {self.id}: {self.title}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'context': self.context,
            'selected_metrics': self.selected_metrics,
            'recommendations': self.recommendations,
            'pdf_path': self.pdf_path,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'created_by': self.created_by,
            'metrics': [metric.to_dict() for metric in self.metrics]
        }


class ExperienceMetric(db.Model):
    """Junction table for experience-metric relationships."""
    __tablename__ = 'experience_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    experience_id = db.Column(db.Integer, db.ForeignKey('experiences.id'), nullable=False)
    metric_id = db.Column(db.Integer, db.ForeignKey('metrics.id'), nullable=False)
    relevance_score = db.Column(db.Float, default=1.0)
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('experience_id', 'metric_id'),)
    
    def __repr__(self):
        return f'<ExperienceMetric {self.experience_id}-{self.metric_id}>'


class ReportMetric(db.Model):
    """Junction table for report-metric relationships."""
    __tablename__ = 'report_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('reports.id'), nullable=False)
    metric_id = db.Column(db.Integer, db.ForeignKey('metrics.id'), nullable=False)
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('report_id', 'metric_id'),)
    
    def __repr__(self):
        return f'<ReportMetric {self.report_id}-{self.metric_id}>'


class EventAnalysis(db.Model):
    """Store event analysis queries and results for organization-specific context."""
    __tablename__ = 'event_analyses'
    
    id = db.Column(db.Integer, primary_key=True)
    event_description = db.Column(db.Text, nullable=False)
    analysis_result = db.Column(db.Text)
    generated_by = db.Column(db.String(100))  # AI model used
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ip_address = db.Column(db.String(45))  # For tracking usage patterns
    
    # Authentication-aware fields
    session_id = db.Column(db.String(100), nullable=True)
    admin_user_id = db.Column(db.Integer, db.ForeignKey('admin_users.id'), nullable=True)
    is_anonymous = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    admin_user = db.relationship('AdminUser', backref='event_analyses')
    
    @validates('event_description')
    def validate_event_description(self, key, value):
        """Validate event description."""
        if not value or not value.strip():
            raise ValueError("Event description cannot be empty")
        if len(value.strip()) > 2000:
            raise ValueError("Event description cannot exceed 2000 characters")
        return value.strip()
    
    def __repr__(self):
        return f'<EventAnalysis {self.id}: {self.event_description[:50]}...>'
    
    def to_dict(self, include_sensitive=False):
        """Convert to dictionary for JSON serialization."""
        data = {
            'id': self.id,
            'event_description': self.event_description,
            'analysis_result': self.analysis_result,
            'generated_by': self.generated_by,
            'success': self.success,
            'error_message': self.error_message,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'is_anonymous': self.is_anonymous,
            'truncated_description': self.event_description[:100] + '...' if len(self.event_description) > 100 else self.event_description
        }
        
        if include_sensitive:
            data.update({
                'ip_address': self.ip_address,
                'session_id': self.session_id,
                'admin_user_id': self.admin_user_id
            })
            
        return data
    
    @classmethod
    def get_recent_searches(cls, limit=5, session_id=None, admin_user_id=None):
        """Get the most recent successful event analyses for a user or session."""
        query = cls.query.filter_by(success=True)
        
        if admin_user_id:
            # Authenticated user - get their personal history
            query = query.filter_by(admin_user_id=admin_user_id)
        elif session_id:
            # Anonymous user - get session-specific history
            query = query.filter_by(session_id=session_id, is_anonymous=True)
        else:
            # Global recent searches (fallback)
            query = query.filter_by(is_anonymous=True)
            
        return query.order_by(cls.created_date.desc()).limit(limit).all()
    
    @classmethod
    def search_by_description(cls, query, session_id=None, admin_user_id=None):
        """Search event analyses by description for a specific user/session."""
        base_query = cls.query
        
        if admin_user_id:
            base_query = base_query.filter_by(admin_user_id=admin_user_id)
        elif session_id:
            base_query = base_query.filter_by(session_id=session_id, is_anonymous=True)
        
        if not query:
            return base_query
        
        search_term = f"%{query}%"
        return base_query.filter(cls.event_description.ilike(search_term))
    
    @classmethod
    def get_user_history(cls, admin_user_id, limit=10):
        """Get event analysis history for authenticated user."""
        return cls.query.filter_by(
            admin_user_id=admin_user_id,
            success=True
        ).order_by(cls.created_date.desc()).limit(limit).all()
    
    @classmethod
    def get_session_history(cls, session_id, limit=5):
        """Get event analysis history for anonymous session."""
        return cls.query.filter_by(
            session_id=session_id,
            is_anonymous=True,
            success=True
        ).order_by(cls.created_date.desc()).limit(limit).all()
    
    @classmethod
    def clear_user_history(cls, admin_user_id):
        """Clear all event analysis history for authenticated user."""
        cls.query.filter_by(admin_user_id=admin_user_id).delete()
        db.session.commit()
        return True
    
    @classmethod
    def clear_session_history(cls, session_id):
        """Clear all event analysis history for anonymous session."""
        cls.query.filter_by(session_id=session_id, is_anonymous=True).delete()
        db.session.commit()
        return True


class SchemaVersion(db.Model):
    """Track database schema versions for migrations."""
    __tablename__ = 'schema_versions'
    
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text)
    applied_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<SchemaVersion {self.version}>'
    
    @classmethod
    def get_current_version(cls):
        """Get the latest applied schema version."""
        latest = cls.query.order_by(cls.applied_date.desc()).first()
        return latest.version if latest else None
    
    @classmethod
    def is_version_applied(cls, version):
        """Check if a specific version has been applied."""
        return cls.query.filter_by(version=version).first() is not None


class UserSession(db.Model):
    """Track user sessions for context management."""
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(255), nullable=False, unique=True, index=True)
    user_identifier = db.Column(db.String(255))  # IP address, user ID, or anonymous identifier
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_activity = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    user_agent = db.Column(db.Text)
    ip_address = db.Column(db.String(45))  # IPv6 compatible
    
    # Relationships - commented out due to session_id type mismatch
    # contexts = db.relationship('UserContext', backref='session', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<UserSession {self.session_id}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_identifier': self.user_identifier,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'is_active': self.is_active,
            'contexts_count': 0  # Disabled due to relationship issue
        }
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)
        db.session.commit()
    
    @classmethod
    def get_or_create(cls, session_id, user_identifier=None, user_agent=None, ip_address=None):
        """Get existing session or create new one."""
        session = cls.query.filter_by(session_id=session_id).first()
        if not session:
            session = cls(
                session_id=session_id,
                user_identifier=user_identifier,
                user_agent=user_agent,
                ip_address=ip_address
            )
            db.session.add(session)
            db.session.commit()
        else:
            session.update_activity()
        return session


class UserContext(db.Model):
    """Store user context data for personalized experiences."""
    __tablename__ = 'user_contexts'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False)
    context_type = db.Column(db.String(50), nullable=False)  # 'search', 'selection', 'preferences', etc.
    context_key = db.Column(db.String(100), nullable=False)  # specific key within context type
    context_data = db.Column(db.Text, nullable=False)  # JSON string of context data
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = db.Column(db.DateTime)  # Optional expiration
    
    # Unique constraint for session + type + key
    __table_args__ = (db.UniqueConstraint('session_id', 'context_type', 'context_key'),)
    
    def __repr__(self):
        return f'<UserContext {self.context_type}:{self.context_key}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        import json
        try:
            parsed_data = json.loads(self.context_data)
        except (json.JSONDecodeError, TypeError):
            parsed_data = self.context_data
            
        return {
            'id': self.id,
            'context_type': self.context_type,
            'context_key': self.context_key,
            'context_data': parsed_data,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'updated_date': self.updated_date.isoformat() if self.updated_date else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }
    
    @validates('context_type', 'context_key')
    def validate_required_fields(self, key, value):
        """Validate required fields."""
        if not value or not value.strip():
            raise ValueError(f"{key.replace('_', ' ').title()} cannot be empty")
        return value.strip()
    
    @validates('context_data')
    def validate_context_data(self, key, value):
        """Validate context data is valid JSON."""
        if not value:
            raise ValueError("Context data cannot be empty")
        
        # Try to parse as JSON to validate format
        import json
        try:
            if isinstance(value, str):
                json.loads(value)
            else:
                json.dumps(value)
        except (json.JSONDecodeError, TypeError):
            raise ValueError("Context data must be valid JSON")
        
        return value if isinstance(value, str) else json.dumps(value)
    
    def is_expired(self):
        """Check if context has expired."""
        if not self.expires_at:
            return False
        # Ensure both datetimes are timezone-aware for comparison
        now = datetime.now(timezone.utc)
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return now > expires_at


class MetricSelection(db.Model):
    """Track user metric selections for context and recommendations."""
    __tablename__ = 'metric_selections'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False)
    metric_id = db.Column(db.Integer, db.ForeignKey('metrics.id'), nullable=False)
    selection_type = db.Column(db.String(50), default='manual')  # 'manual', 'recommended', 'auto'
    selected_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    deselected_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    context_tags = db.Column(db.Text)  # JSON array of context tags
    
    # Relationships
    metric = db.relationship('Metric', backref='selections')
    
    def __repr__(self):
        return f'<MetricSelection {self.metric_id} by session {self.session_id}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        import json
        try:
            tags = json.loads(self.context_tags) if self.context_tags else []
        except (json.JSONDecodeError, TypeError):
            tags = []
            
        return {
            'id': self.id,
            'session_id': self.session_id,
            'metric_id': self.metric_id,
            'metric_name': self.metric.name if self.metric else None,
            'selection_type': self.selection_type,
            'selected_at': self.selected_at.isoformat() if self.selected_at else None,
            'deselected_at': self.deselected_at.isoformat() if self.deselected_at else None,
            'is_active': self.is_active,
            'context_tags': tags
        }
    
    def deselect(self):
        """Mark metric as deselected."""
        self.is_active = False
        self.deselected_at = datetime.now(timezone.utc)
        db.session.commit()
    
    @classmethod
    def get_active_for_session(cls, session_id):
        """Get all active metric selections for a session."""
        return cls.query.filter_by(session_id=session_id, is_active=True).all()
    
    @classmethod
    def toggle_selection(cls, session_id, metric_id, selection_type='manual', context_tags=None):
        """Toggle metric selection for a session."""
        existing = cls.query.filter_by(
            session_id=session_id, 
            metric_id=metric_id, 
            is_active=True
        ).first()
        
        if existing:
            existing.deselect()
            return False, existing  # Deselected
        else:
            import json
            new_selection = cls(
                session_id=session_id,
                metric_id=metric_id,
                selection_type=selection_type,
                context_tags=json.dumps(context_tags) if context_tags else None
            )
            db.session.add(new_selection)
            db.session.commit()
            return True, new_selection  # Selected


class RecommendationEngine(db.Model):
    """Smart AI recommendation engine configuration and state."""
    __tablename__ = 'recommendation_engines'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    model_type = db.Column(db.String(50), default='context_aware')  # 'context_aware', 'collaborative', 'content_based'
    is_active = db.Column(db.Boolean, default=True)
    configuration = db.Column(db.Text)  # JSON configuration
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    recommendations = db.relationship('Recommendation', backref='engine', lazy='dynamic')
    
    def __repr__(self):
        return f'<RecommendationEngine {self.name}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        import json
        try:
            config = json.loads(self.configuration) if self.configuration else {}
        except (json.JSONDecodeError, TypeError):
            config = {}
            
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'model_type': self.model_type,
            'is_active': self.is_active,
            'configuration': config,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'updated_date': self.updated_date.isoformat() if self.updated_date else None,
            'recommendations_count': self.recommendations.count()
        }


class UserPreference(db.Model):
    """Store user preferences for personalized recommendations."""
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False)
    admin_user_id = db.Column(db.Integer, db.ForeignKey('admin_users.id'), nullable=True)
    preference_type = db.Column(db.String(50), nullable=False)  # 'metric_type', 'outcome', 'industry', 'role'
    preference_key = db.Column(db.String(100), nullable=False)  # specific preference identifier
    preference_value = db.Column(db.Text, nullable=False)  # JSON value
    weight = db.Column(db.Float, default=1.0)  # Preference strength (0.0 - 1.0)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    admin_user = db.relationship('AdminUser', backref='preferences')
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('session_id', 'preference_type', 'preference_key'),)
    
    def __repr__(self):
        return f'<UserPreference {self.preference_type}:{self.preference_key}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        import json
        try:
            value = json.loads(self.preference_value)
        except (json.JSONDecodeError, TypeError):
            value = self.preference_value
            
        return {
            'id': self.id,
            'session_id': self.session_id,
            'admin_user_id': self.admin_user_id,
            'preference_type': self.preference_type,
            'preference_key': self.preference_key,
            'preference_value': value,
            'weight': self.weight,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'updated_date': self.updated_date.isoformat() if self.updated_date else None
        }
    
    @classmethod
    def set_preference(cls, session_id, preference_type, preference_key, preference_value, weight=1.0, admin_user_id=None):
        """Set or update a user preference."""
        import json
        
        existing = cls.query.filter_by(
            session_id=session_id,
            preference_type=preference_type,
            preference_key=preference_key
        ).first()
        
        value_json = json.dumps(preference_value) if not isinstance(preference_value, str) else preference_value
        
        if existing:
            existing.preference_value = value_json
            existing.weight = weight
            existing.admin_user_id = admin_user_id
            existing.updated_date = datetime.now(timezone.utc)
        else:
            existing = cls(
                session_id=session_id,
                admin_user_id=admin_user_id,
                preference_type=preference_type,
                preference_key=preference_key,
                preference_value=value_json,
                weight=weight
            )
            db.session.add(existing)
        
        db.session.commit()
        return existing
    
    @classmethod
    def get_preferences(cls, session_id, preference_type=None):
        """Get user preferences for a session."""
        query = cls.query.filter_by(session_id=session_id)
        if preference_type:
            query = query.filter_by(preference_type=preference_type)
        return query.all()


class Recommendation(db.Model):
    """Store AI-generated recommendations with context."""
    __tablename__ = 'recommendations'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False)
    engine_id = db.Column(db.Integer, db.ForeignKey('recommendation_engines.id'), nullable=False)
    recommendation_type = db.Column(db.String(50), nullable=False)  # 'metric', 'outcome', 'analysis'
    target_id = db.Column(db.Integer)  # ID of recommended item (metric_id, outcome_id, etc.)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    reasoning = db.Column(db.Text)  # Why this was recommended
    confidence_score = db.Column(db.Float, default=0.5)  # 0.0 - 1.0
    context_data = db.Column(db.Text)  # JSON context used for recommendation
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # User interaction tracking
    viewed_at = db.Column(db.DateTime)
    clicked_at = db.Column(db.DateTime)
    dismissed_at = db.Column(db.DateTime)
    accepted_at = db.Column(db.DateTime)
    
    # Relationships (removed session relationship due to string session_id)
    feedbacks = db.relationship('RecommendationFeedback', backref='recommendation', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Recommendation {self.id}: {self.title}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        import json
        try:
            context = json.loads(self.context_data) if self.context_data else {}
        except (json.JSONDecodeError, TypeError):
            context = {}
            
        return {
            'id': self.id,
            'session_id': self.session_id,
            'engine_id': self.engine_id,
            'recommendation_type': self.recommendation_type,
            'target_id': self.target_id,
            'title': self.title,
            'description': self.description,
            'reasoning': self.reasoning,
            'confidence_score': self.confidence_score,
            'context_data': context,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'viewed_at': self.viewed_at.isoformat() if self.viewed_at else None,
            'clicked_at': self.clicked_at.isoformat() if self.clicked_at else None,
            'dismissed_at': self.dismissed_at.isoformat() if self.dismissed_at else None,
            'accepted_at': self.accepted_at.isoformat() if self.accepted_at else None,
            'feedback_count': self.feedbacks.count()
        }
    
    def mark_viewed(self):
        """Mark recommendation as viewed."""
        if not self.viewed_at:
            self.viewed_at = datetime.now(timezone.utc)
            db.session.commit()
    
    def mark_clicked(self):
        """Mark recommendation as clicked."""
        if not self.clicked_at:
            self.clicked_at = datetime.now(timezone.utc)
            db.session.commit()
    
    def mark_dismissed(self):
        """Mark recommendation as dismissed."""
        if not self.dismissed_at:
            self.dismissed_at = datetime.now(timezone.utc)
            db.session.commit()
    
    def mark_accepted(self):
        """Mark recommendation as accepted."""
        if not self.accepted_at:
            self.accepted_at = datetime.now(timezone.utc)
            db.session.commit()
    
    @classmethod
    def get_for_session(cls, session_id, recommendation_type=None, limit=10):
        """Get recommendations for a session."""
        query = cls.query.filter_by(session_id=session_id)
        if recommendation_type:
            query = query.filter_by(recommendation_type=recommendation_type)
        return query.order_by(cls.confidence_score.desc(), cls.created_date.desc()).limit(limit).all()
    
    @classmethod
    def get_active_for_session(cls, session_id, recommendation_type=None):
        """Get active (not dismissed) recommendations for a session."""
        query = cls.query.filter_by(session_id=session_id).filter(cls.dismissed_at.is_(None))
        if recommendation_type:
            query = query.filter_by(recommendation_type=recommendation_type)
        return query.order_by(cls.confidence_score.desc(), cls.created_date.desc()).all()


class RecommendationFeedback(db.Model):
    """Track user feedback on recommendations for learning."""
    __tablename__ = 'recommendation_feedbacks'
    
    id = db.Column(db.Integer, primary_key=True)
    recommendation_id = db.Column(db.Integer, db.ForeignKey('recommendations.id'), nullable=False)
    feedback_type = db.Column(db.String(50), nullable=False)  # 'rating', 'useful', 'not_useful', 'irrelevant'
    feedback_value = db.Column(db.String(100))  # Rating value, boolean, or category
    feedback_text = db.Column(db.Text)  # Optional user comment
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ip_address = db.Column(db.String(45))
    
    def __repr__(self):
        return f'<RecommendationFeedback {self.recommendation_id}: {self.feedback_type}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'recommendation_id': self.recommendation_id,
            'feedback_type': self.feedback_type,
            'feedback_value': self.feedback_value,
            'feedback_text': self.feedback_text,
            'created_date': self.created_date.isoformat() if self.created_date else None
        }
    
    @classmethod
    def add_feedback(cls, recommendation_id, feedback_type, feedback_value=None, feedback_text=None, ip_address=None):
        """Add feedback for a recommendation."""
        feedback = cls(
            recommendation_id=recommendation_id,
            feedback_type=feedback_type,
            feedback_value=feedback_value,
            feedback_text=feedback_text,
            ip_address=ip_address
        )
        db.session.add(feedback)
        db.session.commit()
        return feedback
    
    @classmethod
    def get_feedback_summary(cls, recommendation_id):
        """Get feedback summary for a recommendation."""
        feedbacks = cls.query.filter_by(recommendation_id=recommendation_id).all()
        
        summary = {
            'total_feedback': len(feedbacks),
            'positive': 0,
            'negative': 0,
            'neutral': 0,
            'average_rating': None,
            'feedback_types': {}
        }
        
        ratings = []
        for feedback in feedbacks:
            # Count feedback types
            if feedback.feedback_type not in summary['feedback_types']:
                summary['feedback_types'][feedback.feedback_type] = 0
            summary['feedback_types'][feedback.feedback_type] += 1
            
            # Categorize sentiment
            if feedback.feedback_type in ['useful', 'helpful', 'relevant']:
                summary['positive'] += 1
            elif feedback.feedback_type in ['not_useful', 'unhelpful', 'irrelevant']:
                summary['negative'] += 1
            else:
                summary['neutral'] += 1
            
            # Collect ratings
            if feedback.feedback_type == 'rating' and feedback.feedback_value:
                try:
                    ratings.append(float(feedback.feedback_value))
                except ValueError:
                    pass
        
        if ratings:
            summary['average_rating'] = sum(ratings) / len(ratings)
        
        return summary


class RecommendationHistory(db.Model):
    """Track recommendation generation history and performance."""
    __tablename__ = 'recommendation_history'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False)
    engine_id = db.Column(db.Integer, db.ForeignKey('recommendation_engines.id'), nullable=False)
    generation_context = db.Column(db.Text)  # JSON context at time of generation
    recommendations_generated = db.Column(db.Integer, default=0)
    recommendations_accepted = db.Column(db.Integer, default=0)
    recommendations_dismissed = db.Column(db.Integer, default=0)
    average_confidence = db.Column(db.Float)
    generation_time_ms = db.Column(db.Integer)  # Time taken to generate recommendations
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships (removed session relationship due to string session_id)
    engine = db.relationship('RecommendationEngine', backref='histories')
    
    def __repr__(self):
        return f'<RecommendationHistory {self.id}: {self.recommendations_generated} generated>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        import json
        try:
            context = json.loads(self.generation_context) if self.generation_context else {}
        except (json.JSONDecodeError, TypeError):
            context = {}
            
        return {
            'id': self.id,
            'session_id': self.session_id,
            'engine_id': self.engine_id,
            'generation_context': context,
            'recommendations_generated': self.recommendations_generated,
            'recommendations_accepted': self.recommendations_accepted,
            'recommendations_dismissed': self.recommendations_dismissed,
            'average_confidence': self.average_confidence,
            'generation_time_ms': self.generation_time_ms,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'acceptance_rate': self.recommendations_accepted / self.recommendations_generated if self.recommendations_generated > 0 else 0,
            'dismissal_rate': self.recommendations_dismissed / self.recommendations_generated if self.recommendations_generated > 0 else 0
        }
    
    @classmethod
    def create_entry(cls, session_id, engine_id, generation_context, recommendations_count, average_confidence, generation_time_ms):
        """Create a new recommendation history entry."""
        import json
        
        history = cls(
            session_id=session_id,
            engine_id=engine_id,
            generation_context=json.dumps(generation_context) if not isinstance(generation_context, str) else generation_context,
            recommendations_generated=recommendations_count,
            average_confidence=average_confidence,
            generation_time_ms=generation_time_ms
        )
        db.session.add(history)
        db.session.commit()
        return history
    
    def update_stats(self, accepted_count=None, dismissed_count=None):
        """Update recommendation statistics."""
        if accepted_count is not None:
            self.recommendations_accepted = accepted_count
        if dismissed_count is not None:
            self.recommendations_dismissed = dismissed_count
        db.session.commit()


class ReportTemplate(db.Model):
    """PDF report templates for dynamic generation."""
    __tablename__ = 'report_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    template_type = db.Column(db.String(50), nullable=False)  # 'comprehensive', 'basic'
    sections = db.Column(db.Text, nullable=False)  # JSON array of section configurations
    styling = db.Column(db.Text)  # JSON styling configuration
    is_active = db.Column(db.Boolean, default=True)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('admin_users.id'))
    
    # Relationships
    reports = db.relationship('DynamicReport', backref='template', lazy='dynamic')
    
    def __repr__(self):
        return f'<ReportTemplate {self.name}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        import json
        try:
            sections = json.loads(self.sections) if self.sections else []
            styling = json.loads(self.styling) if self.styling else {}
        except (json.JSONDecodeError, TypeError):
            sections = []
            styling = {}
            
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'template_type': self.template_type,
            'sections': sections,
            'styling': styling,
            'is_active': self.is_active,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'updated_date': self.updated_date.isoformat() if self.updated_date else None,
            'created_by': self.created_by,
            'reports_count': self.reports.count()
        }


class DynamicReport(db.Model):
    """Dynamic PDF reports with context-aware content."""
    __tablename__ = 'dynamic_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('report_templates.id'), nullable=False)
    session_id = db.Column(db.String(100), nullable=False)
    
    # Report configuration
    selected_outcomes = db.Column(db.Text)  # JSON array of outcome IDs
    selected_metrics = db.Column(db.Text)  # JSON array of metric IDs
    ai_recommendations = db.Column(db.Text)  # JSON array of AI recommendation data
    generation_context = db.Column(db.Text)  # JSON context used for generation
    
    # Content sections (dynamically generated)
    executive_summary = db.Column(db.Text)
    strategy_context = db.Column(db.Text)
    metric_analysis = db.Column(db.Text)
    ai_insights = db.Column(db.Text)
    implementation_roadmap = db.Column(db.Text)
    success_metrics = db.Column(db.Text)
    appendices = db.Column(db.Text)
    
    # Generation metadata
    generation_status = db.Column(db.String(50), default='pending')  # 'pending', 'generating', 'completed', 'failed'
    generation_progress = db.Column(db.Integer, default=0)  # 0-100
    estimated_pages = db.Column(db.Integer)
    actual_pages = db.Column(db.Integer)
    generation_time_ms = db.Column(db.Integer)
    
    # File information
    pdf_path = db.Column(db.String(500))
    file_size_bytes = db.Column(db.Integer)
    download_count = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    generated_date = db.Column(db.DateTime)
    last_downloaded = db.Column(db.DateTime)
    
    # Relationships
    session = db.relationship('UserSession', backref='dynamic_reports')
    
    def __repr__(self):
        return f'<DynamicReport {self.id}: {self.title}>'
    
    def to_dict(self, include_content=False):
        """Convert to dictionary for JSON serialization."""
        import json
        
        try:
            outcomes = json.loads(self.selected_outcomes) if self.selected_outcomes else []
            metrics = json.loads(self.selected_metrics) if self.selected_metrics else []
            recommendations = json.loads(self.ai_recommendations) if self.ai_recommendations else []
            context = json.loads(self.generation_context) if self.generation_context else {}
        except (json.JSONDecodeError, TypeError):
            outcomes = []
            metrics = []
            recommendations = []
            context = {}
            
        data = {
            'id': self.id,
            'title': self.title,
            'template_id': self.template_id,
            'template_name': self.template.name if self.template else None,
            'template_type': self.template.template_type if self.template else None,
            'session_id': self.session_id,
            'selected_outcomes': outcomes,
            'selected_metrics': metrics,
            'ai_recommendations': recommendations,
            'generation_context': context,
            'generation_status': self.generation_status,
            'generation_progress': self.generation_progress,
            'estimated_pages': self.estimated_pages,
            'actual_pages': self.actual_pages,
            'generation_time_ms': self.generation_time_ms,
            'pdf_path': self.pdf_path,
            'file_size_bytes': self.file_size_bytes,
            'download_count': self.download_count,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'generated_date': self.generated_date.isoformat() if self.generated_date else None,
            'last_downloaded': self.last_downloaded.isoformat() if self.last_downloaded else None
        }
        
        if include_content:
            data.update({
                'executive_summary': self.executive_summary,
                'strategy_context': self.strategy_context,
                'metric_analysis': self.metric_analysis,
                'ai_insights': self.ai_insights,
                'implementation_roadmap': self.implementation_roadmap,
                'success_metrics': self.success_metrics,
                'appendices': self.appendices
            })
            
        return data
    
    def update_progress(self, progress, status=None):
        """Update generation progress."""
        self.generation_progress = min(100, max(0, progress))
        if status:
            self.generation_status = status
        db.session.commit()
    
    def mark_completed(self, pdf_path, file_size_bytes, actual_pages, generation_time_ms):
        """Mark report generation as completed."""
        self.generation_status = 'completed'
        self.generation_progress = 100
        self.pdf_path = pdf_path
        self.file_size_bytes = file_size_bytes
        self.actual_pages = actual_pages
        self.generation_time_ms = generation_time_ms
        self.generated_date = datetime.now(timezone.utc)
        db.session.commit()
    
    def mark_failed(self, error_message=None):
        """Mark report generation as failed."""
        self.generation_status = 'failed'
        if error_message:
            # Store error in generation_context
            import json
            try:
                context = json.loads(self.generation_context) if self.generation_context else {}
            except (json.JSONDecodeError, TypeError):
                context = {}
            context['error'] = error_message
            self.generation_context = json.dumps(context)
        db.session.commit()
    
    def increment_download(self):
        """Increment download counter."""
        self.download_count += 1
        self.last_downloaded = datetime.now(timezone.utc)
        db.session.commit()
    
    @classmethod
    def create_report(cls, title, template_id, session_id, selected_outcomes, selected_metrics, ai_recommendations=None, generation_context=None):
        """Create a new dynamic report."""
        import json
        
        report = cls(
            title=title,
            template_id=template_id,
            session_id=session_id,
            selected_outcomes=json.dumps(selected_outcomes) if selected_outcomes else '[]',
            selected_metrics=json.dumps(selected_metrics) if selected_metrics else '[]',
            ai_recommendations=json.dumps(ai_recommendations) if ai_recommendations else '[]',
            generation_context=json.dumps(generation_context) if generation_context else '{}'
        )
        db.session.add(report)
        db.session.commit()
        return report
    
    @classmethod
    def get_for_session(cls, session_id, limit=10):
        """Get reports for a session."""
        return cls.query.filter_by(session_id=session_id).order_by(cls.created_date.desc()).limit(limit).all()


class ReportSection(db.Model):
    """Individual report sections with dynamic content."""
    __tablename__ = 'report_sections'
    
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('dynamic_reports.id'), nullable=False)
    section_type = db.Column(db.String(50), nullable=False)  # 'executive_summary', 'metric_analysis', etc.
    section_title = db.Column(db.String(200), nullable=False)
    section_content = db.Column(db.Text)
    section_order = db.Column(db.Integer, default=0)
    page_count = db.Column(db.Integer, default=1)
    generation_notes = db.Column(db.Text)  # Notes about how this section was generated
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    report = db.relationship('DynamicReport', backref='sections')
    
    def __repr__(self):
        return f'<ReportSection {self.section_type} for Report {self.report_id}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'report_id': self.report_id,
            'section_type': self.section_type,
            'section_title': self.section_title,
            'section_content': self.section_content,
            'section_order': self.section_order,
            'page_count': self.page_count,
            'generation_notes': self.generation_notes,
            'created_date': self.created_date.isoformat() if self.created_date else None
        }


class ReportAnalytics(db.Model):
    """Analytics for report generation and usage."""
    __tablename__ = 'report_analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('dynamic_reports.id'), nullable=False)
    
    # Content analysis
    outcome_distribution = db.Column(db.Text)  # JSON of outcome usage
    metric_type_distribution = db.Column(db.Text)  # JSON of metric type usage
    ai_recommendation_count = db.Column(db.Integer, default=0)
    complexity_score = db.Column(db.Float)  # 0.0-1.0 based on selections
    
    # Generation metrics
    content_generation_time = db.Column(db.Integer)  # milliseconds
    pdf_generation_time = db.Column(db.Integer)  # milliseconds
    total_generation_time = db.Column(db.Integer)  # milliseconds
    
    # Usage metrics
    view_count = db.Column(db.Integer, default=0)
    share_count = db.Column(db.Integer, default=0)
    feedback_score = db.Column(db.Float)  # Average user feedback
    
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    report = db.relationship('DynamicReport', backref='analytics', uselist=False)
    
    def __repr__(self):
        return f'<ReportAnalytics for Report {self.report_id}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        import json
        try:
            outcome_dist = json.loads(self.outcome_distribution) if self.outcome_distribution else {}
            metric_dist = json.loads(self.metric_type_distribution) if self.metric_type_distribution else {}
        except (json.JSONDecodeError, TypeError):
            outcome_dist = {}
            metric_dist = {}
            
        return {
            'id': self.id,
            'report_id': self.report_id,
            'outcome_distribution': outcome_dist,
            'metric_type_distribution': metric_dist,
            'ai_recommendation_count': self.ai_recommendation_count,
            'complexity_score': self.complexity_score,
            'content_generation_time': self.content_generation_time,
            'pdf_generation_time': self.pdf_generation_time,
            'total_generation_time': self.total_generation_time,
            'view_count': self.view_count,
            'share_count': self.share_count,
            'feedback_score': self.feedback_score,
            'created_date': self.created_date.isoformat() if self.created_date else None
        }
    
    @classmethod
    def create_analytics(cls, report_id, outcome_distribution, metric_type_distribution, ai_recommendation_count, complexity_score):
        """Create analytics entry for a report."""
        import json
        
        analytics = cls(
            report_id=report_id,
            outcome_distribution=json.dumps(outcome_distribution),
            metric_type_distribution=json.dumps(metric_type_distribution),
            ai_recommendation_count=ai_recommendation_count,
            complexity_score=complexity_score
        )
        db.session.add(analytics)
        db.session.commit()
        return analytics
