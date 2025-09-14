"""
New model classes for experience tracking and report generation
"""

from datetime import datetime
from app import db
from sqlalchemy import event
from sqlalchemy.orm import validates


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
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
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
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
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


class SchemaVersion(db.Model):
    """Track database schema versions for migrations."""
    __tablename__ = 'schema_versions'
    
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text)
    applied_date = db.Column(db.DateTime, default=datetime.utcnow)
    
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
