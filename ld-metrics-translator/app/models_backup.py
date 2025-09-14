from datetime import datetime, timezone
from sqlalchemy import event
from sqlalchemy.orm import validates
from werkzeug.security import generate_password_hash, check_password_hash
from . import db


class LDOutcome(db.Model):
    """L&D Outcome categories (Engagement, Retention, etc.)."""
    __tablename__ = 'ld_outcomes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    color = db.Column(db.String(7), default='#007bff')  # Hex color for UI
    icon = db.Column(db.String(50), default='fas fa-chart-line')  # FontAwesome icon class
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    metrics = db.relationship('Metric', backref='outcome', lazy='dynamic')
    
    def __repr__(self):
        return f'<LDOutcome {self.name}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'color': self.color,
            'icon': self.icon,
            'sort_order': self.sort_order,
            'is_active': self.is_active,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'metrics_count': self.metrics.count()
        }


class MetricType(db.Model):
    """Types of metrics (KPI, Behavioral, etc.)."""
    __tablename__ = 'metric_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    color = db.Column(db.String(7), default='#28a745')  # Hex color for UI
    icon = db.Column(db.String(50), default='fas fa-cog')  # FontAwesome icon class
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    metrics = db.relationship('Metric', backref='metric_type', lazy='dynamic')
    
    def __repr__(self):
        return f'<MetricType {self.name}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'color': self.color,
            'icon': self.icon,
            'sort_order': self.sort_order,
            'is_active': self.is_active,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'metrics_count': self.metrics.count()
        }


class Metric(db.Model):
    """Individual metrics within each outcome and type."""
    __tablename__ = 'metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    outcome_id = db.Column(db.Integer, db.ForeignKey('ld_outcomes.id'), nullable=False)
    metric_type_id = db.Column(db.Integer, db.ForeignKey('metric_types.id'), nullable=False)
    
    # Measurement details
    measurement_method = db.Column(db.Text)
    data_source = db.Column(db.String(200))
    frequency = db.Column(db.String(50))  # daily, weekly, monthly, quarterly
    unit_of_measure = db.Column(db.String(50))
    
    # Metadata
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<Metric {self.name}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'outcome_id': self.outcome_id,
            'outcome_name': self.outcome.name if self.outcome else None,
            'metric_type_id': self.metric_type_id,
            'metric_type_name': self.metric_type.name if self.metric_type else None,
            'measurement_method': self.measurement_method,
            'data_source': self.data_source,
            'frequency': self.frequency,
            'unit_of_measure': self.unit_of_measure,
            'is_active': self.is_active,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'updated_date': self.updated_date.isoformat() if self.updated_date else None
        }


class AdminUser(db.Model):
    """Admin users for the application."""
    __tablename__ = 'admin_users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)
    
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
            'is_active': self.is_active,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


# Note: db is imported from app/__init__.py
