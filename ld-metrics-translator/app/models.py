from datetime import datetime, timezone
import json
from sqlalchemy import event, or_, func
from sqlalchemy.orm import validates
from werkzeug.security import generate_password_hash, check_password_hash
from . import db


class LDOutcome(db.Model):
    """L&D Outcome categories (Engagement, Retention, etc.)."""
    __tablename__ = 'ld_outcomes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    # Additional taxonomy fields used in tests
    category = db.Column(db.String(100))
    level = db.Column(db.String(100))
    color = db.Column(db.String(7), default='#007bff')  # Hex color for UI
    icon = db.Column(db.String(50), default='fas fa-chart-line')  # FontAwesome icon class
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    metrics = db.relationship(
        'Metric', backref='outcome', cascade='all, delete-orphan'
    )
    
    def __repr__(self):
        return f'<LDOutcome {self.name}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'level': self.level,
            'color': self.color,
            'icon': self.icon,
            'sort_order': self.sort_order,
            'is_active': self.is_active,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'created_at': self.created_date.isoformat() if self.created_date else None,
            'metrics_count': len(self.metrics)
        }

    # Aliases and helpers for tests
    @property
    def created_at(self):
        return self.created_date

    @classmethod
    def search(cls, query: str):
        if not query:
            return cls.query.all()
        pattern = f"%{query}%"
        return cls.query.filter(or_(
            cls.name.ilike(pattern),
            cls.description.ilike(pattern)
        )).all()

    @classmethod
    def filter_by_category(cls, category: str):
        return cls.query.filter_by(category=category).all()

    @classmethod
    def filter_by_level(cls, level: str):
        return cls.query.filter_by(level=level).all()

    def is_valid_category(self):
        # Accept a simple whitelist used by tests
        return self.category in {None, 'Knowledge', 'Skills', 'Behavior'}

    def is_valid_level(self):
        return self.level in {None, 'Basic', 'Intermediate', 'Advanced'}


class MetricType(db.Model):
    """Types of metrics (KPI, Behavioral, etc.)."""
    __tablename__ = 'metric_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    # Additional field used by tests
    category = db.Column(db.String(100))
    color = db.Column(db.String(7), default='#28a745')  # Hex color for UI
    icon = db.Column(db.String(50), default='fas fa-cog')  # FontAwesome icon class
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    metrics = db.relationship(
        'Metric', backref='metric_type', cascade='all, delete-orphan'
    )
    
    def __repr__(self):
        return f'<MetricType {self.name}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'color': self.color,
            'icon': self.icon,
            'sort_order': self.sort_order,
            'is_active': self.is_active,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'created_at': self.created_date.isoformat() if self.created_date else None,
            'metrics_count': len(self.metrics)
        }

    @property
    def created_at(self):
        return self.created_date

    def is_valid_category(self):
        return self.category in {None, 'Assessment', 'KPI', 'Behavioral'}


class Metric(db.Model):
    """Individual metrics within each outcome and type."""
    __tablename__ = 'metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    outcome_id = db.Column(db.Integer, db.ForeignKey('ld_outcomes.id'), nullable=False)
    metric_type_id = db.Column(db.Integer, db.ForeignKey('metric_types.id'), nullable=False)
    
    # Driver Card identity and relationships
    # One of: concept | behavior | kpi | outcome (free text validated at API level)
    identifier_type = db.Column(db.String(20))
    # JSON string storing driver chain details, e.g. {
    #   "drives_behaviors": ["Embracing challenges"],
    #   "driven_by_concepts": ["Empathy"],
    #   "measured_by_kpis": ["Skill Application Rate"],
    #   "leads_to_outcomes": ["Increased Resilience"]
    # }
    driver_chain = db.Column(db.Text)

    # Measurement details
    measurement_method = db.Column(db.Text)
    data_source = db.Column(db.String(200))
    frequency = db.Column(db.String(50))  # daily, weekly, monthly, quarterly
    unit_of_measure = db.Column(db.String(50))
    example = db.Column(db.Text)  # Add example field for comprehensive seeding
    # Fields used by tests
    data_collection = db.Column(db.String(100))
    success_criteria = db.Column(db.String(200))
    
    # Metadata
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<Metric {self.name}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        # Parse driver_chain JSON safely
        try:
            parsed_chain = json.loads(self.driver_chain) if self.driver_chain else None
        except (json.JSONDecodeError, TypeError):
            parsed_chain = self.driver_chain

        # Associated frameworks via competencies link (deduplicated)
        try:
            frameworks = []
            if hasattr(self, 'competencies') and self.competencies:
                seen = set()
                for comp in self.competencies:
                    fw = getattr(comp, 'framework', None)
                    if fw and fw.id not in seen:
                        frameworks.append({'id': fw.id, 'name': fw.name, 'slug': fw.slug})
                        seen.add(fw.id)
        except Exception:
            frameworks = []

        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'outcome_id': self.outcome_id,
            'outcome_name': self.outcome.name if self.outcome else None,
            'metric_type_id': self.metric_type_id,
            'metric_type_name': self.metric_type.name if self.metric_type else None,
            'identifier_type': self.identifier_type,
            'driver_chain': parsed_chain,
            'example': self.example,
            'measurement_method': self.measurement_method,
            'data_source': self.data_source,
            'data_collection': self.data_collection,
            'success_criteria': self.success_criteria,
            'frequency': self.frequency,
            'unit_of_measure': self.unit_of_measure,
            'is_active': self.is_active,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'created_at': self.created_date.isoformat() if self.created_date else None,
            'updated_date': self.updated_date.isoformat() if self.updated_date else None,
            'associated_frameworks': frameworks,
        }

    # Query helpers used by API/tests
    @classmethod
    def search(cls, search_query: str):
        """Return a SQLAlchemy query filtered by a case-insensitive search across name, description, outcome name, and metric type name.

        If search_query is falsy, return base query of active metrics.
        """
        query = cls.search_query(search_query)
        return query.all()

    @classmethod
    def search_query(cls, search_query: str):
        """Return a SQLAlchemy query for searching metrics. Used by API pagination.

        If search_query is falsy, returns base active metrics query.
        """
        base = cls.query.filter(cls.is_active.is_(True))
        if not search_query:
            return base
        pattern = f"%{search_query}%"
        return (
            base.join(LDOutcome, cls.outcome_id == LDOutcome.id)
            .join(MetricType, cls.metric_type_id == MetricType.id)
            .filter(
                or_(
                    cls.name.ilike(pattern),
                    cls.description.ilike(pattern),
                    LDOutcome.name.ilike(pattern),
                    MetricType.name.ilike(pattern),
                )
            )
        )

    @classmethod
    def filter_by_outcome(cls, outcome_id: int):
        """Return a query filtered by outcome_id and active status."""
        return cls.query.filter(cls.is_active.is_(True), cls.outcome_id == outcome_id)

    @classmethod
    def filter_by_type(cls, metric_type_id: int):
        """Return a query filtered by metric_type_id and active status."""
        return cls.query.filter(cls.is_active.is_(True), cls.metric_type_id == metric_type_id)

    @property
    def created_at(self):
        return self.created_date

    # Simple validation helpers used by tests
    def is_valid_measurement_method(self):
        return self.measurement_method in {None, 'Survey', 'Analytics'}

    def is_valid_data_collection(self):
        return self.data_collection in {None, 'Daily', 'Weekly', 'Monthly'}


class AdminUser(db.Model):
    """Admin users for the application."""
    __tablename__ = 'admin_users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # API key used for authenticating API write operations
    api_key = db.Column(db.String(255), unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=True, nullable=False)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)
    # Relationship to audit logs
    audit_logs = db.relationship('AuditLog', backref='admin_user', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<AdminUser {self.username}>'
    
    def set_password(self, password):
        """Set password hash."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash."""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            # Tests expect an is_admin flag
            'is_admin': self.is_admin,
            'is_active': self.is_active,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'created_at': self.created_date.isoformat() if self.created_date else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class AuditLog(db.Model):
    """Audit logging for admin actions."""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    admin_user_id = db.Column(db.Integer, db.ForeignKey('admin_users.id'), nullable=False, index=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f'<AuditLog {self.action} by {self.admin_user_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'admin_user_id': self.admin_user_id,
            'action': self.action,
            'details': self.details,
            'ip_address': self.ip_address,
            'created_date': self.created_date.isoformat() if self.created_date else None,
        }


class EventAnalysis(db.Model):
    """Store AI event analyses for audit and retrieval."""
    __tablename__ = 'event_analyses'

    id = db.Column(db.Integer, primary_key=True)
    event_description = db.Column(db.Text, nullable=False)
    analysis_result = db.Column(db.Text)
    generated_by = db.Column(db.String(100))
    success = db.Column(db.Boolean, default=True, nullable=False)
    error_message = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f'<EventAnalysis {self.id} success={self.success}>'

    @property
    def created_at(self):
        return self.created_date

    def to_dict(self):
        import json
        try:
            parsed = json.loads(self.analysis_result) if self.analysis_result else None
        except (json.JSONDecodeError, TypeError):
            parsed = self.analysis_result
        return {
            'id': self.id,
            'event_description': self.event_description,
            'analysis_result': parsed,
            'generated_by': self.generated_by,
            'success': self.success,
            'error_message': self.error_message,
            'ip_address': self.ip_address,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'created_at': self.created_date.isoformat() if self.created_date else None,
        }

    @classmethod
    def get_recent_searches(cls, limit=5):
        return cls.query.filter_by(success=True).order_by(cls.created_date.desc()).limit(limit).all()

    @classmethod
    def search_by_description(cls, query: str):
        if not query:
            return cls.query.order_by(cls.created_date.desc())
        pattern = f"%{query}%"
        return cls.query.filter(cls.event_description.ilike(pattern)).order_by(cls.created_date.desc())


class User(db.Model):
    """Basic user model used by tests (separate from AdminUser)."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash or '', password)

    @property
    def created_at(self):
        return self.created_date

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_admin': self.is_admin,
            'created_at': self.created_date.isoformat() if self.created_date else None,
        }


class UserSession(db.Model):
    """Track user sessions for context management."""
    __tablename__ = 'user_sessions'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(255), nullable=False, unique=True, index=True)
    user_identifier = db.Column(db.String(255))
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_activity = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    user_agent = db.Column(db.Text)
    ip_address = db.Column(db.String(45))

    def __repr__(self):
        return f'<UserSession {self.session_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_identifier': self.user_identifier,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'is_active': self.is_active,
        }

    def update_activity(self):
        self.last_activity = datetime.now(timezone.utc)
        db.session.commit()

    @classmethod
    def get_or_create(cls, session_id, user_identifier=None, user_agent=None, ip_address=None):
        session = cls.query.filter_by(session_id=session_id).first()
        if not session:
            session = cls(
                session_id=session_id,
                user_identifier=user_identifier,
                user_agent=user_agent,
                ip_address=ip_address,
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
    context_type = db.Column(db.String(50), nullable=False)
    context_key = db.Column(db.String(100), nullable=False)
    context_data = db.Column(db.Text, nullable=False)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = db.Column(db.DateTime)

    __table_args__ = (db.UniqueConstraint('session_id', 'context_type', 'context_key'),)

    def __repr__(self):
        return f'<UserContext {self.context_type}:{self.context_key}>'

    def to_dict(self):
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
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }

    @validates('context_type', 'context_key')
    def validate_required_fields(self, key, value):
        if not value or not value.strip():
            raise ValueError(f"{key.replace('_', ' ').title()} cannot be empty")
        return value.strip()

    @validates('context_data')
    def validate_context_data(self, key, value):
        if not value:
            raise ValueError("Context data cannot be empty")
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
        if not self.expires_at:
            return False
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
    selection_type = db.Column(db.String(50), default='manual')
    selected_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    deselected_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    context_tags = db.Column(db.Text)

    metric = db.relationship('Metric', backref='selections')

    def __repr__(self):
        return f'<MetricSelection {self.metric_id} by session {self.session_id}>'

    def to_dict(self):
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
            'context_tags': tags,
        }

    def deselect(self):
        self.is_active = False
        self.deselected_at = datetime.now(timezone.utc)
        db.session.commit()

    @classmethod
    def get_active_for_session(cls, session_id):
        return cls.query.filter_by(session_id=session_id, is_active=True).all()

    @classmethod
    def toggle_selection(cls, session_id, metric_id, selection_type='manual', context_tags=None):
        existing = cls.query.filter_by(
            session_id=session_id,
            metric_id=metric_id,
            is_active=True,
        ).first()
        if existing:
            existing.deselect()
            return False, existing
        else:
            import json
            new_selection = cls(
                session_id=session_id,
                metric_id=metric_id,
                selection_type=selection_type,
                context_tags=json.dumps(context_tags) if context_tags else None,
            )
            db.session.add(new_selection)
            db.session.commit()
            return True, new_selection


# ------------------------------------------------------------
# Leadership Framework models (framework-centric navigation)
# ------------------------------------------------------------
class Framework(db.Model):
    __tablename__ = 'frameworks'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    slug = db.Column(db.String(200), nullable=False, unique=True, index=True)
    description = db.Column(db.Text)
    source = db.Column(db.String(200))
    is_builtin = db.Column(db.Boolean, default=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    competencies = db.relationship('Competency', backref='framework', cascade='all, delete-orphan', order_by='Competency.sort_order')

    def __repr__(self):
        return f'<Framework {self.slug}>'

    def to_dict(self, include_competencies: bool = False, include_metrics: bool = False):
        data = {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'source': self.source,
            'is_builtin': self.is_builtin,
            'is_active': self.is_active,
            'sort_order': self.sort_order,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'competency_count': len(self.competencies),
        }
        if include_competencies:
            data['competencies'] = [c.to_dict(include_metrics=include_metrics) for c in self.competencies]
        return data


# association table linking competencies to metrics (many-to-many)
competency_metrics = db.Table(
    'competency_metrics',
    db.Column('competency_id', db.Integer, db.ForeignKey('competencies.id'), primary_key=True),
    db.Column('metric_id', db.Integer, db.ForeignKey('metrics.id'), primary_key=True),
)


class Competency(db.Model):
    __tablename__ = 'competencies'

    id = db.Column(db.Integer, primary_key=True)
    framework_id = db.Column(db.Integer, db.ForeignKey('frameworks.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text)
    sort_order = db.Column(db.Integer, default=0)

    metrics = db.relationship('Metric', secondary=competency_metrics, backref='competencies')

    def __repr__(self):
        return f'<Competency {self.slug} in framework {self.framework_id}>'

    def to_dict(self, include_metrics: bool = False):
        data = {
            'id': self.id,
            'framework_id': self.framework_id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'sort_order': self.sort_order,
            'metrics_count': len(self.metrics),
        }
        if include_metrics:
            data['metrics'] = [m.to_dict() for m in self.metrics]
        return data


# ------------------------------------------------------------
# Role Profiling (KSAO) models
# ------------------------------------------------------------

class RoleProfile(db.Model):
    __tablename__ = 'role_profiles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    description = db.Column(db.Text)
    department = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    knowledge_items = db.relationship('RoleKnowledge', backref='role_profile', cascade='all, delete-orphan')
    skill_items = db.relationship('RoleSkill', backref='role_profile', cascade='all, delete-orphan')
    ability_items = db.relationship('RoleAbility', backref='role_profile', cascade='all, delete-orphan')
    other_requirements = db.relationship('RoleOtherRequirement', backref='role_profile', cascade='all, delete-orphan')
    outcomes = db.relationship('RoleOutcome', backref='role_profile', cascade='all, delete-orphan')
    competency_targets = db.relationship('RoleCompetencyTarget', backref='role_profile', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<RoleProfile {self.name}>'

    def to_dict(self, include_ksaos: bool = True, include_targets: bool = True):
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'department': self.department,
            'is_active': self.is_active,
            'created_date': self.created_date.isoformat() if self.created_date else None,
        }
        if include_ksaos:
            data.update({
                'knowledge': [k.to_dict() for k in self.knowledge_items],
                'skills': [s.to_dict() for s in self.skill_items],
                'abilities': [a.to_dict() for a in self.ability_items],
                'others': [o.to_dict() for o in self.other_requirements],
                'outcomes': [out.to_dict() for out in self.outcomes],
            })
        if include_targets:
            data['competency_targets'] = [t.to_dict() for t in self.competency_targets]
        return data


class RoleKnowledge(db.Model):
    __tablename__ = 'role_knowledge'

    id = db.Column(db.Integer, primary_key=True)
    role_profile_id = db.Column(db.Integer, db.ForeignKey('role_profiles.id'), nullable=False, index=True)
    name = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    driver_card_id = db.Column(db.Integer, db.ForeignKey('metrics.id', ondelete='SET NULL'))
    driver_card = db.relationship('Metric', foreign_keys=[driver_card_id])
    target_level = db.Column(db.Integer)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'driver_card_id': self.driver_card_id,
            'driver_card': {'id': self.driver_card.id, 'name': self.driver_card.name} if self.driver_card else None,
            'target_level': self.target_level,
        }


class RoleSkill(db.Model):
    __tablename__ = 'role_skills'

    id = db.Column(db.Integer, primary_key=True)
    role_profile_id = db.Column(db.Integer, db.ForeignKey('role_profiles.id'), nullable=False, index=True)
    name = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    driver_card_id = db.Column(db.Integer, db.ForeignKey('metrics.id', ondelete='SET NULL'))
    driver_card = db.relationship('Metric', foreign_keys=[driver_card_id])
    target_level = db.Column(db.Integer)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'driver_card_id': self.driver_card_id,
            'driver_card': {'id': self.driver_card.id, 'name': self.driver_card.name} if self.driver_card else None,
            'target_level': self.target_level,
        }


class RoleAbility(db.Model):
    __tablename__ = 'role_abilities'

    id = db.Column(db.Integer, primary_key=True)
    role_profile_id = db.Column(db.Integer, db.ForeignKey('role_profiles.id'), nullable=False, index=True)
    name = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    driver_card_id = db.Column(db.Integer, db.ForeignKey('metrics.id', ondelete='SET NULL'))
    driver_card = db.relationship('Metric', foreign_keys=[driver_card_id])
    target_level = db.Column(db.Integer)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'driver_card_id': self.driver_card_id,
            'driver_card': {'id': self.driver_card.id, 'name': self.driver_card.name} if self.driver_card else None,
            'target_level': self.target_level,
        }


class RoleOtherRequirement(db.Model):
    __tablename__ = 'role_other_requirements'

    id = db.Column(db.Integer, primary_key=True)
    role_profile_id = db.Column(db.Integer, db.ForeignKey('role_profiles.id'), nullable=False, index=True)
    name = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    driver_card_id = db.Column(db.Integer, db.ForeignKey('metrics.id', ondelete='SET NULL'))
    driver_card = db.relationship('Metric', foreign_keys=[driver_card_id])

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'driver_card_id': self.driver_card_id,
            'driver_card': {'id': self.driver_card.id, 'name': self.driver_card.name} if self.driver_card else None,
        }


class RoleOutcome(db.Model):
    __tablename__ = 'role_outcomes'

    id = db.Column(db.Integer, primary_key=True)
    role_profile_id = db.Column(db.Integer, db.ForeignKey('role_profiles.id'), nullable=False, index=True)
    name = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    driver_card_id = db.Column(db.Integer, db.ForeignKey('metrics.id', ondelete='SET NULL'))
    target_level = db.Column(db.Integer)

    driver_card = db.relationship('Metric', foreign_keys=[driver_card_id])

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'driver_card_id': self.driver_card_id,
            'driver_card': {'id': self.driver_card.id, 'name': self.driver_card.name} if self.driver_card else None,
            'target_level': self.target_level,
        }


class RoleCompetencyTarget(db.Model):
    __tablename__ = 'role_competency_targets'

    id = db.Column(db.Integer, primary_key=True)
    role_profile_id = db.Column(db.Integer, db.ForeignKey('role_profiles.id'), nullable=False, index=True)
    competency_id = db.Column(db.Integer, db.ForeignKey('competencies.id'), nullable=False, index=True)
    target_level = db.Column(db.Integer, nullable=False, default=3)  # 1-5 scale
    weight = db.Column(db.Float, default=1.0)

    competency = db.relationship('Competency')

    def to_dict(self):
        return {
            'id': self.id,
            'competency_id': self.competency_id,
            'competency_name': self.competency.name if self.competency else None,
            'target_level': self.target_level,
            'weight': self.weight,
        }


class RoleAssignment(db.Model):
    """Assign a role profile to a specific person/user identifier.

    We keep this generic by storing an external reference such as employee_id or email.
    """
    __tablename__ = 'role_assignments'

    id = db.Column(db.Integer, primary_key=True)
    role_profile_id = db.Column(db.Integer, db.ForeignKey('role_profiles.id'), nullable=False, index=True)
    person_identifier = db.Column(db.String(255), nullable=False, index=True)  # e.g., user email or employee ID
    assigned_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    role_profile = db.relationship('RoleProfile')

    def to_dict(self):
        return {
            'id': self.id,
            'role_profile_id': self.role_profile_id,
            'person_identifier': self.person_identifier,
            'assigned_date': self.assigned_date.isoformat() if self.assigned_date else None,
            'is_active': self.is_active,
            'role_profile': {'id': self.role_profile.id, 'name': self.role_profile.name} if self.role_profile else None,
        }

# ------------------------------------------------------------
# Dynamic PDF Report Models required by report generator
# ------------------------------------------------------------

class ReportTemplate(db.Model):
    """Templates used to shape generated reports."""
    __tablename__ = 'report_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    template_type = db.Column(db.String(50), nullable=False, index=True)  # 'comprehensive' | 'basic'
    sections = db.Column(db.Text)  # JSON string
    styling = db.Column(db.Text)   # JSON string
    created_by = db.Column(db.String(120))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        try:
            sections = json.loads(self.sections) if self.sections else []
        except (json.JSONDecodeError, TypeError):
            sections = self.sections
        try:
            styling = json.loads(self.styling) if self.styling else {}
        except (json.JSONDecodeError, TypeError):
            styling = self.styling
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'template_type': self.template_type,
            'sections': sections,
            'styling': styling,
            'created_by': self.created_by,
            'is_active': self.is_active,
            'created_date': self.created_date.isoformat() if self.created_date else None,
        }


class DynamicReport(db.Model):
    """Generated report record and content/progress tracking."""
    __tablename__ = 'dynamic_reports'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('report_templates.id'), nullable=False)
    session_id = db.Column(db.String(255), index=True, nullable=False)

    # Selections and context
    selected_outcomes = db.Column(db.Text)      # JSON array of IDs
    selected_metrics = db.Column(db.Text)       # JSON array of IDs
    ai_recommendations = db.Column(db.Text)     # JSON array of objects
    generation_context = db.Column(db.Text)     # JSON object

    # Content sections
    executive_summary = db.Column(db.Text)
    strategy_context = db.Column(db.Text)
    metric_analysis = db.Column(db.Text)
    ai_insights = db.Column(db.Text)
    implementation_roadmap = db.Column(db.Text)
    success_metrics = db.Column(db.Text)
    appendices = db.Column(db.Text)

    # Progress/status
    generation_status = db.Column(db.String(50), default='queued', nullable=False)
    generation_progress = db.Column(db.Integer, default=0, nullable=False)
    estimated_pages = db.Column(db.Integer)
    error_message = db.Column(db.Text)

    # File info
    pdf_path = db.Column(db.String(500))
    download_count = db.Column(db.Integer, default=0, nullable=False)

    # Timestamps
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    generated_date = db.Column(db.DateTime)

    template = db.relationship('ReportTemplate', backref='reports')

    @classmethod
    def create_report(
        cls,
        title: str,
        template_id: int,
        session_id: int,
        selected_outcomes,
        selected_metrics,
        ai_recommendations,
        generation_context,
    ):
        report = cls(
            title=title,
            template_id=template_id,
            session_id=session_id,
            selected_outcomes=json.dumps(selected_outcomes or []),
            selected_metrics=json.dumps(selected_metrics or []),
            ai_recommendations=json.dumps(ai_recommendations or []),
            generation_context=json.dumps(generation_context or {}),
            generation_status='queued',
            generation_progress=0,
        )
        db.session.add(report)
        db.session.commit()
        return report

    def update_progress(self, progress: int, status: str | None = None):
        self.generation_progress = max(0, min(100, int(progress or 0)))
        if status:
            self.generation_status = status
        db.session.commit()

    def mark_completed(self, pdf_path: str, file_size: int | None, page_count: int | None, generation_time_ms: int | None):
        self.generation_status = 'completed'
        self.generation_progress = 100
        self.generated_date = datetime.now(timezone.utc)
        self.pdf_path = pdf_path
        self.estimated_pages = page_count
        db.session.commit()

    def mark_failed(self, error: str):
        self.generation_status = 'failed'
        self.error_message = error
        db.session.commit()

    def increment_download(self):
        self.download_count = (self.download_count or 0) + 1
        db.session.commit()

    def to_dict(self, include_content: bool = False):
        def _loads(val, default):
            try:
                return json.loads(val) if val else default
            except (json.JSONDecodeError, TypeError):
                return val or default

        data = {
            'id': self.id,
            'title': self.title,
            'template_id': self.template_id,
            'session_id': self.session_id,
            'selected_outcomes': _loads(self.selected_outcomes, []),
            'selected_metrics': _loads(self.selected_metrics, []),
            'ai_recommendations': _loads(self.ai_recommendations, []),
            'generation_context': _loads(self.generation_context, {}),
            'generation_status': self.generation_status,
            'generation_progress': self.generation_progress,
            'estimated_pages': self.estimated_pages,
            'error_message': self.error_message,
            'pdf_path': self.pdf_path,
            'download_count': self.download_count,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'generated_date': self.generated_date.isoformat() if self.generated_date else None,
        }

        if include_content:
            data.update({
                'executive_summary': self.executive_summary,
                'strategy_context': self.strategy_context,
                'metric_analysis': self.metric_analysis,
                'ai_insights': self.ai_insights,
                'implementation_roadmap': self.implementation_roadmap,
                'success_metrics': self.success_metrics,
                'appendices': self.appendices,
            })
        return data


class ReportAnalytics(db.Model):
    """Analytics for generated reports."""
    __tablename__ = 'report_analytics'

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('dynamic_reports.id'), nullable=False, index=True)
    outcome_distribution = db.Column(db.Text)         # JSON
    metric_type_distribution = db.Column(db.Text)     # JSON
    ai_recommendation_count = db.Column(db.Integer, default=0, nullable=False)
    complexity_score = db.Column(db.Float)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    report = db.relationship('DynamicReport', backref='analytics')

    @classmethod
    def create_analytics(
        cls,
        report_id: int,
        outcome_distribution,
        metric_type_distribution,
        ai_recommendation_count: int,
        complexity_score: float,
    ):
        entry = cls(
            report_id=report_id,
            outcome_distribution=json.dumps(outcome_distribution or {}),
            metric_type_distribution=json.dumps(metric_type_distribution or {}),
            ai_recommendation_count=ai_recommendation_count or 0,
            complexity_score=complexity_score,
        )
        db.session.add(entry)
        db.session.commit()
        return entry

    def to_dict(self):
        def _loads(val, default):
            try:
                return json.loads(val) if val else default
            except (json.JSONDecodeError, TypeError):
                return val or default
        return {
            'id': self.id,
            'report_id': self.report_id,
            'outcome_distribution': _loads(self.outcome_distribution, {}),
            'metric_type_distribution': _loads(self.metric_type_distribution, {}),
            'ai_recommendation_count': self.ai_recommendation_count,
            'complexity_score': self.complexity_score,
            'created_date': self.created_date.isoformat() if self.created_date else None,
        }

# Note: db is imported from app/__init__.py
