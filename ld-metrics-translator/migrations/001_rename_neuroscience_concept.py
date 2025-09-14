"""
Migration 001: Rename 'Neuroscience Concept' to 'Neuroscience-Based Metric'
Date: 2025-08-08
Description: Updates the metric type name and adds new tables for experience tracking and report generation
"""

from datetime import datetime
from app import db
from app.models import MetricType, Metric

def upgrade():
    """Apply the migration."""
    print("Starting Migration 001: Rename Neuroscience Concept...")
    
    try:
        # 1. Update the metric type name
        neuroscience_type = MetricType.query.filter_by(name='Neuroscience Concept').first()
        if neuroscience_type:
            neuroscience_type.name = 'Neuroscience-Based Metric'
            print("+ Renamed 'Neuroscience Concept' to 'Neuroscience-Based Metric'")
        else:
            print("! 'Neuroscience Concept' metric type not found")
        
        # 2. Create new tables for experience tracking
        with db.engine.connect() as conn:
            conn.execute(db.text("""
                CREATE TABLE IF NOT EXISTS experiences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id VARCHAR(100),
                    employee_name VARCHAR(200),
                    context TEXT NOT NULL,
                    experience_description TEXT NOT NULL,
                    outcomes TEXT,
                    keywords TEXT,
                    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_by INTEGER,
                    FOREIGN KEY (created_by) REFERENCES admin_users (id)
                )
            """))
            conn.commit()
        print("+ Created 'experiences' table")
        
        # 3. Create table for report generation
        with db.engine.connect() as conn:
            conn.execute(db.text("""
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title VARCHAR(200) NOT NULL,
                    context TEXT NOT NULL,
                    selected_metrics TEXT NOT NULL,
                    recommendations TEXT,
                    pdf_path VARCHAR(500),
                    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_by INTEGER,
                    FOREIGN KEY (created_by) REFERENCES admin_users (id)
                )
            """))
            conn.commit()
        print("+ Created 'reports' table")
        
        # 4. Create junction table for report-metric relationships
        with db.engine.connect() as conn:
            conn.execute(db.text("""
                CREATE TABLE IF NOT EXISTS report_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id INTEGER NOT NULL,
                    metric_id INTEGER NOT NULL,
                    FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE CASCADE,
                    FOREIGN KEY (metric_id) REFERENCES metrics (id) ON DELETE CASCADE,
                    UNIQUE(report_id, metric_id)
                )
            """))
            conn.commit()
        print("+ Created 'report_metrics' junction table")
        
        # 5. Create table for experience-metric relationships
        with db.engine.connect() as conn:
            conn.execute(db.text("""
                CREATE TABLE IF NOT EXISTS experience_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    experience_id INTEGER NOT NULL,
                    metric_id INTEGER NOT NULL,
                    relevance_score FLOAT DEFAULT 1.0,
                    FOREIGN KEY (experience_id) REFERENCES experiences (id) ON DELETE CASCADE,
                    FOREIGN KEY (metric_id) REFERENCES metrics (id) ON DELETE CASCADE,
                    UNIQUE(experience_id, metric_id)
                )
            """))
            conn.commit()
        print("+ Created 'experience_metrics' junction table")
        
        # 6. Add version tracking table
        with db.engine.connect() as conn:
            conn.execute(db.text("""
                CREATE TABLE IF NOT EXISTS schema_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version VARCHAR(50) NOT NULL UNIQUE,
                    description TEXT,
                    applied_date DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
        print("+ Created 'schema_versions' table")
        
        # 7. Record this migration
        with db.engine.connect() as conn:
            conn.execute(db.text("""
                INSERT OR IGNORE INTO schema_versions (version, description) 
                VALUES ('001', 'Rename Neuroscience Concept and add experience/report tables')
            """))
            conn.commit()
        
        # Commit all changes
        db.session.commit()
        print("SUCCESS: Migration 001 completed successfully!")
        return True
        
    except Exception as e:
        print(f"ERROR: Migration 001 failed: {str(e)}")
        db.session.rollback()
        return False

def downgrade():
    """Rollback the migration."""
    print("Rolling back Migration 001...")
    
    try:
        # 1. Revert the metric type name
        neuroscience_type = MetricType.query.filter_by(name='Neuroscience-Based Metric').first()
        if neuroscience_type:
            neuroscience_type.name = 'Neuroscience Concept'
            print("+ Reverted 'Neuroscience-Based Metric' back to 'Neuroscience Concept'")
        
        # 2. Drop new tables (in reverse order due to foreign keys)
        tables_to_drop = [
            'experience_metrics',
            'report_metrics', 
            'reports',
            'experiences'
        ]
        
        for table in tables_to_drop:
            with db.engine.connect() as conn:
                conn.execute(db.text(f"DROP TABLE IF EXISTS {table}"))
                conn.commit()
            print(f"+ Dropped table '{table}'")
        
        # 3. Remove version record
        with db.engine.connect() as conn:
            conn.execute(db.text("DELETE FROM schema_versions WHERE version = '001'"))
            conn.commit()
        
        # Commit rollback
        db.session.commit()
        print("SUCCESS: Migration 001 rollback completed!")
        return True
        
    except Exception as e:
        print(f"ERROR: Migration 001 rollback failed: {str(e)}")
        db.session.rollback()
        return False

if __name__ == "__main__":
    # Can be run directly for testing
    print("Migration 001 - Use upgrade() or downgrade() functions")
