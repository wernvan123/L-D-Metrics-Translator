"""Database initialization and utility functions for L&D Metrics Translator."""

from app import db
from flask import current_app
from app.models import LDOutcome, MetricType, Metric, EventAnalysis
from datetime import datetime


def init_database():
    """Initialize database with tables."""
    try:
        if current_app and current_app.config.get('TESTING'):
            db.drop_all()
            db.create_all()
        else:
            db.create_all()
    except RuntimeError:
        # Fallback if no app context
        db.create_all()
    print("Database tables created successfully!")


def seed_basic_data():
    """Seed the database with basic L&D outcomes, metric types, and sample metrics."""
    try:
        # Do not seed during tests; many tests expect empty starting state
        try:
            if current_app and current_app.config.get('TESTING'):
                return
        except Exception:
            pass
        # We'll seed idempotently by name; no early return based on counts
        
        # L&D Outcomes
        outcomes = [
            {
                'name': 'Employee Engagement',
                'description': 'Measures how engaged and motivated employees are with their learning and development',
                'color': '#4CAF50',
                'icon': 'fas fa-heart',
                'sort_order': 1
            },
            {
                'name': 'Skill Development',
                'description': 'Tracks the acquisition and improvement of specific skills and competencies',
                'color': '#2196F3',
                'icon': 'fas fa-graduation-cap',
                'sort_order': 2
            },
            {
                'name': 'Performance Improvement',
                'description': 'Measures the impact of L&D on job performance and productivity',
                'color': '#FF9800',
                'icon': 'fas fa-chart-line',
                'sort_order': 3
            },
            {
                'name': 'Career Advancement',
                'description': 'Tracks career progression and internal mobility as a result of L&D',
                'color': '#9C27B0',
                'icon': 'fas fa-rocket',
                'sort_order': 4
            },
            {
                'name': 'Business Impact',
                'description': 'Measures the overall business impact and ROI of L&D initiatives',
                'color': '#F44336',
                'icon': 'fas fa-dollar-sign',
                'sort_order': 5
            }
        ]
        
        # Metric Types
        types = [
            {
                'name': 'KPI Metrics',
                'description': 'Key Performance Indicators that directly measure L&D effectiveness',
                'color': '#607D8B',
                'icon': 'fas fa-tachometer-alt',
                'sort_order': 1
            },
            {
                'name': 'Behavioral Metrics',
                'description': 'Metrics that track changes in employee behavior and engagement',
                'color': '#795548',
                'icon': 'fas fa-users',
                'sort_order': 2
            },
            {
                'name': 'Business Metrics',
                'description': 'Metrics that connect L&D activities to business outcomes',
                'color': '#3F51B5',
                'icon': 'fas fa-briefcase',
                'sort_order': 3
            }
        ]
        
        # Upsert outcomes by name
        name_to_outcome = {}
        for outcome_data in outcomes:
            existing = LDOutcome.query.filter_by(name=outcome_data['name']).first()
            if existing:
                # Update attributes if changed
                for k, v in outcome_data.items():
                    setattr(existing, k, v)
                obj = existing
            else:
                obj = LDOutcome(**outcome_data)
                db.session.add(obj)
            name_to_outcome[outcome_data['name']] = obj
        
        # Upsert metric types by name
        name_to_type = {}
        for type_data in types:
            existing = MetricType.query.filter_by(name=type_data['name']).first()
            if existing:
                for k, v in type_data.items():
                    setattr(existing, k, v)
                obj = existing
            else:
                obj = MetricType(**type_data)
                db.session.add(obj)
            name_to_type[type_data['name']] = obj
        
        db.session.commit()
        
        # Now create sample metrics (idempotent by name + outcome/type)
        sample_metrics = [
            # Employee Engagement metrics
            {'name': 'Training Completion Rate', 'description': 'Percentage of employees completing assigned training', 'outcome': 'Employee Engagement', 'metric_type': 'KPI Metrics', 'frequency': 'monthly'},
            {'name': 'Learning Engagement Score', 'description': 'Employee satisfaction with learning programs', 'outcome': 'Employee Engagement', 'metric_type': 'Behavioral Metrics', 'frequency': 'quarterly'},
            {'name': 'Voluntary Training Participation', 'description': 'Rate of voluntary participation in optional training', 'outcome': 'Employee Engagement', 'metric_type': 'Behavioral Metrics', 'frequency': 'monthly'},
            
            # Skill Development metrics
            {'name': 'Skill Assessment Scores', 'description': 'Pre and post-training skill assessment results', 'outcome': 'Skill Development', 'metric_type': 'KPI Metrics', 'frequency': 'quarterly'},
            {'name': 'Certification Achievement Rate', 'description': 'Percentage of employees achieving certifications', 'outcome': 'Skill Development', 'metric_type': 'KPI Metrics', 'frequency': 'quarterly'},
            {'name': 'Skills Gap Closure', 'description': 'Reduction in identified skills gaps', 'outcome': 'Skill Development', 'metric_type': 'Business Metrics', 'frequency': 'annually'},
            
            # Performance Improvement metrics
            {'name': 'Performance Review Scores', 'description': 'Employee performance ratings post-training', 'outcome': 'Performance Improvement', 'metric_type': 'KPI Metrics', 'frequency': 'quarterly'},
            {'name': 'Productivity Metrics', 'description': 'Measurable productivity improvements', 'outcome': 'Performance Improvement', 'metric_type': 'Business Metrics', 'frequency': 'monthly'},
            {'name': 'Quality Improvement', 'description': 'Reduction in errors and quality issues', 'outcome': 'Performance Improvement', 'metric_type': 'Business Metrics', 'frequency': 'monthly'},
            
            # Career Advancement metrics
            {'name': 'Internal Promotion Rate', 'description': 'Rate of internal promotions for trained employees', 'outcome': 'Career Advancement', 'metric_type': 'KPI Metrics', 'frequency': 'annually'},
            {'name': 'Career Path Progression', 'description': 'Movement along defined career paths', 'outcome': 'Career Advancement', 'metric_type': 'Behavioral Metrics', 'frequency': 'quarterly'},
            {'name': 'Leadership Pipeline Strength', 'description': 'Number of employees ready for leadership roles', 'outcome': 'Career Advancement', 'metric_type': 'Business Metrics', 'frequency': 'annually'},
            
            # Business Impact metrics
            {'name': 'Training ROI', 'description': 'Return on investment for training programs', 'outcome': 'Business Impact', 'metric_type': 'Business Metrics', 'frequency': 'annually'},
            {'name': 'Employee Retention Rate', 'description': 'Retention rate of employees who received training', 'outcome': 'Business Impact', 'metric_type': 'KPI Metrics', 'frequency': 'quarterly'},
            {'name': 'Revenue per Employee', 'description': 'Revenue generated per trained employee', 'outcome': 'Business Impact', 'metric_type': 'Business Metrics', 'frequency': 'quarterly'},
        ]

        for metric_def in sample_metrics:
            outcome_obj = name_to_outcome.get(metric_def['outcome']) or LDOutcome.query.filter_by(name=metric_def['outcome']).first()
            type_obj = name_to_type.get(metric_def['metric_type']) or MetricType.query.filter_by(name=metric_def['metric_type']).first()
            if not outcome_obj or not type_obj:
                # Skip if dependencies missing (shouldn't happen)
                continue
            existing_metric = Metric.query.filter_by(
                name=metric_def['name'],
                outcome_id=outcome_obj.id,
                metric_type_id=type_obj.id,
            ).first()
            if existing_metric:
                # Update description/frequency if changed
                existing_metric.description = metric_def['description']
                existing_metric.frequency = metric_def.get('frequency')
            else:
                db.session.add(Metric(
                    name=metric_def['name'],
                    description=metric_def['description'],
                    outcome_id=outcome_obj.id,
                    metric_type_id=type_obj.id,
                    frequency=metric_def.get('frequency'),
                ))
        
        db.session.commit()
        print(f"Basic data seeded successfully!")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error seeding basic data: {e}")
        raise


def seed_sample_metrics():
    """Seed database with sample metrics for testing."""
    
    # Check if metrics already exist
    if Metric.query.first():
        print("Sample metrics already exist. Skipping seed.")
        return
    
    # Get the seeded outcomes and types
    engagement = LDOutcome.query.filter_by(name='Employee Engagement').first()
    retention = LDOutcome.query.filter_by(name='Employee Retention').first()
    behavior_change = LDOutcome.query.filter_by(name='Behavior Change').first()
    performance = LDOutcome.query.filter_by(name='Performance').first()
    well_being = LDOutcome.query.filter_by(name='Well-being').first()
    
    operational_kpi = MetricType.query.filter_by(name='Operational KPI').first()
    behavioral_metric = MetricType.query.filter_by(name='Behavioral Metric').first()
    neuroscience_concept = MetricType.query.filter_by(name='Neuroscience-Based Metric').first()
    
    if not all([engagement, retention, behavior_change, performance, well_being, 
                operational_kpi, behavioral_metric, neuroscience_concept]):
        print("Basic data not found. Please run seed_basic_data() first.")
        return
    
    # Sample metrics
    sample_metrics = [
        {
            'name': 'Employee Net Promoter Score',
            'description': 'Measures employee loyalty and likelihood to recommend the organization as a place to work.',
            'example': 'Survey question: "How likely are you to recommend this company as a place to work?" Scale: 0-10',
            'outcome_id': engagement.id,
            'metric_type_id': operational_kpi.id
        },
        {
            'name': 'Active Participation in Workshops',
            'description': 'Tracks the level of active engagement during learning sessions.',
            'example': 'Percentage of participants asking questions, contributing to discussions, or completing activities.',
            'outcome_id': engagement.id,
            'metric_type_id': behavioral_metric.id
        },
        {
            'name': 'Attention',
            'description': 'The cognitive process of selectively concentrating on learning content.',
            'example': 'Measured through eye-tracking, EEG, or sustained attention tasks during learning.',
            'outcome_id': engagement.id,
            'metric_type_id': neuroscience_concept.id
        },
        {
            'name': 'Voluntary Turnover Rate',
            'description': 'Percentage of employees who choose to leave the organization.',
            'example': 'Calculate: (Number of voluntary departures / Average number of employees) × 100',
            'outcome_id': retention.id,
            'metric_type_id': operational_kpi.id
        },
        {
            'name': 'Memory Consolidation',
            'description': 'The process by which temporary memories become stable long-term memories.',
            'example': 'Assessed through spaced repetition testing and retention curves over time.',
            'outcome_id': behavior_change.id,
            'metric_type_id': neuroscience_concept.id
        }
    ]
    
    try:
        for metric_data in sample_metrics:
            metric = Metric(**metric_data)
            db.session.add(metric)
        
        db.session.commit()
        print(f"Sample metrics seeded successfully! Created {len(sample_metrics)} metrics.")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error seeding sample metrics: {str(e)}")
        raise


def reset_database():
    """Drop all tables and recreate them. WARNING: This will delete all data!"""
    print("WARNING: This will delete all existing data!")
    confirm = input("Type 'YES' to confirm database reset: ")
    
    if confirm == 'YES':
        db.drop_all()
        db.create_all()
        print("Database reset successfully!")
    else:
        print("Database reset cancelled.")


def get_database_stats():
    """Print current database statistics."""
    outcomes_count = LDOutcome.query.count()
    types_count = MetricType.query.count()
    metrics_count = Metric.query.count()
    # analyses_count = EventAnalysis.query.count()  # Commented out as EventAnalysis model doesn't exist in simplified version
    analyses_count = 0
    
    print("\n=== Database Statistics ===")
    print(f"L&D Outcomes: {outcomes_count}")
    print(f"Metric Types: {types_count}")
    print(f"Metrics: {metrics_count}")
    print(f"Event Analyses: {analyses_count}")
    print("===========================\n")
    
    return {
        'outcomes': outcomes_count,
        'types': types_count,
        'metrics': metrics_count,
        'analyses': analyses_count
    }


# Event Analysis CRUD Operations
def create_event_analysis(event_description, analysis_result=None, generated_by=None, 
                         success=True, error_message=None, ip_address=None):
    """Create a new event analysis record."""
    try:
        analysis = EventAnalysis(
            event_description=event_description,
            analysis_result=analysis_result,
            generated_by=generated_by,
            success=success,
            error_message=error_message,
            ip_address=ip_address
        )
        db.session.add(analysis)
        db.session.commit()
        return analysis
    except Exception as e:
        db.session.rollback()
        print(f"Error creating event analysis: {str(e)}")
        raise


def get_recent_event_analyses(limit=5):
    """Get the most recent successful event analyses."""
    try:
        return EventAnalysis.query.filter_by(success=True)\
                                 .order_by(EventAnalysis.created_date.desc())\
                                 .limit(limit).all()
    except Exception as e:
        print(f"Error retrieving recent event analyses: {str(e)}")
        return []


def get_event_analysis_by_id(analysis_id):
    """Get a specific event analysis by ID."""
    try:
        return EventAnalysis.query.get(analysis_id)
    except Exception as e:
        print(f"Error retrieving event analysis {analysis_id}: {str(e)}")
        return None


def search_event_analyses(query, limit=10):
    """Search event analyses by description."""
    try:
        if not query:
            return EventAnalysis.query.order_by(EventAnalysis.created_date.desc()).limit(limit).all()
        
        search_term = f"%{query}%"
        return EventAnalysis.query.filter(
            EventAnalysis.event_description.ilike(search_term)
        ).order_by(EventAnalysis.created_date.desc()).limit(limit).all()
    except Exception as e:
        print(f"Error searching event analyses: {str(e)}")
        return []


def delete_event_analysis(analysis_id):
    """Delete an event analysis by ID."""
    try:
        analysis = EventAnalysis.query.get(analysis_id)
        if analysis:
            db.session.delete(analysis)
            db.session.commit()
            return True
        return False
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting event analysis {analysis_id}: {str(e)}")
        return False


if __name__ == '__main__':
    # This allows running the script directly for testing
    from app import create_app
    
    app = create_app()
    with app.app_context():
        init_database()
        seed_basic_data()
        seed_sample_metrics()
        get_database_stats()
