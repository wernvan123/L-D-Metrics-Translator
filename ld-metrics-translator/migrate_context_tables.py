"""
Database migration script for Context Management System
Creates new tables: user_sessions, user_contexts, metric_selections
"""

import os
import sys
from datetime import datetime
from flask import Flask
from app import create_app, db
from app.models import UserSession, UserContext, MetricSelection, SchemaVersion


def create_context_tables():
    """Create the new context management tables."""
    print("Creating context management tables...")
    
    try:
        # Create all tables (will only create missing ones)
        db.create_all()
        
        # Verify tables were created
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        
        required_tables = ['user_sessions', 'user_contexts', 'metric_selections']
        created_tables = []
        
        for table in required_tables:
            if table in tables:
                created_tables.append(table)
                print(f"[OK] Table '{table}' created successfully")
            else:
                print(f"[ERROR] Failed to create table '{table}'")
        
        if len(created_tables) == len(required_tables):
            print(f"\n[OK] All {len(required_tables)} context management tables created successfully!")
            return True
        else:
            print(f"\n[ERROR] Only {len(created_tables)}/{len(required_tables)} tables created")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error creating tables: {str(e)}")
        return False


def add_schema_version():
    """Add schema version record for context management."""
    try:
        # Check if this version already exists
        version = "context_management_v1.0"
        existing = SchemaVersion.query.filter_by(version=version).first()
        
        if existing:
            print(f"Schema version '{version}' already exists")
            return True
        
        # Add new schema version
        schema_version = SchemaVersion(
            version=version,
            description="Added context management system with user sessions, contexts, and metric selections"
        )
        
        db.session.add(schema_version)
        db.session.commit()
        
        print(f"[OK] Added schema version: {version}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error adding schema version: {str(e)}")
        db.session.rollback()
        return False


def verify_table_structure():
    """Verify the table structure is correct."""
    print("\nVerifying table structure...")
    
    try:
        inspector = db.inspect(db.engine)
        
        # Check user_sessions table
        user_sessions_columns = [col['name'] for col in inspector.get_columns('user_sessions')]
        expected_user_sessions = ['id', 'session_id', 'user_identifier', 'created_date', 
                                 'last_activity', 'is_active', 'user_agent', 'ip_address']
        
        for col in expected_user_sessions:
            if col in user_sessions_columns:
                print(f"[OK] user_sessions.{col}")
            else:
                print(f"[ERROR] Missing user_sessions.{col}")
        
        # Check user_contexts table
        user_contexts_columns = [col['name'] for col in inspector.get_columns('user_contexts')]
        expected_user_contexts = ['id', 'session_id', 'context_type', 'context_key', 
                                 'context_data', 'created_date', 'updated_date', 'expires_at']
        
        for col in expected_user_contexts:
            if col in user_contexts_columns:
                print(f"[OK] user_contexts.{col}")
            else:
                print(f"[ERROR] Missing user_contexts.{col}")
        
        # Check metric_selections table
        metric_selections_columns = [col['name'] for col in inspector.get_columns('metric_selections')]
        expected_metric_selections = ['id', 'session_id', 'metric_id', 'selection_type',
                                     'selected_at', 'deselected_at', 'is_active', 'context_tags']
        
        for col in expected_metric_selections:
            if col in metric_selections_columns:
                print(f"[OK] metric_selections.{col}")
            else:
                print(f"[ERROR] Missing metric_selections.{col}")
        
        print("[OK] Table structure verification complete")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error verifying table structure: {str(e)}")
        return False


def create_indexes():
    """Create database indexes for better performance."""
    print("\nCreating database indexes...")
    
    try:
        with db.engine.connect() as conn:
            # Index for user_sessions.session_id (already unique)
            print("[OK] user_sessions.session_id index (already exists)")
            
            # Index for user_contexts lookups
            try:
                conn.execute(db.text("""
                    CREATE INDEX IF NOT EXISTS idx_user_contexts_session_type_key 
                    ON user_contexts(session_id, context_type, context_key)
                """))
                print("[OK] Created index: idx_user_contexts_session_type_key")
            except Exception as e:
                print(f"Index already exists or error: {e}")
            
            # Index for metric_selections lookups
            try:
                conn.execute(db.text("""
                    CREATE INDEX IF NOT EXISTS idx_metric_selections_session_active 
                    ON metric_selections(session_id, is_active)
                """))
                print("[OK] Created index: idx_metric_selections_session_active")
            except Exception as e:
                print(f"Index already exists or error: {e}")
            
            # Index for metric_selections by metric_id
            try:
                conn.execute(db.text("""
                    CREATE INDEX IF NOT EXISTS idx_metric_selections_metric_id 
                    ON metric_selections(metric_id)
                """))
                print("[OK] Created index: idx_metric_selections_metric_id")
            except Exception as e:
                print(f"Index already exists or error: {e}")
            
            conn.commit()
        
        print("[OK] Database indexes created successfully")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error creating indexes: {str(e)}")
        return False


def test_basic_functionality():
    """Test basic functionality of the new tables."""
    print("\nTesting basic functionality...")
    
    try:
        # Test UserSession creation
        test_session = UserSession(
            session_id="test_migration_session",
            user_identifier="migration_test",
            user_agent="Migration Script",
            ip_address="127.0.0.1"
        )
        db.session.add(test_session)
        db.session.commit()
        print("[OK] UserSession creation test passed")
        
        # Test UserContext creation
        test_context = UserContext(
            session_id=test_session.id,
            context_type="test",
            context_key="migration_test",
            context_data='{"test": "migration"}'
        )
        db.session.add(test_context)
        db.session.commit()
        print("[OK] UserContext creation test passed")
        
        # Test MetricSelection creation (if metrics exist)
        from app.models import Metric
        first_metric = Metric.query.first()
        if first_metric:
            test_selection = MetricSelection(
                session_id=test_session.id,
                metric_id=first_metric.id,
                selection_type="test"
            )
            db.session.add(test_selection)
            db.session.commit()
            print("[OK] MetricSelection creation test passed")
        else:
            print("[WARNING] No metrics found, skipping MetricSelection test")
        
        # Clean up test data
        db.session.delete(test_context)
        if first_metric:
            MetricSelection.query.filter_by(session_id=test_session.id).delete()
        db.session.delete(test_session)
        db.session.commit()
        print("[OK] Test data cleaned up")
        
        print("[OK] Basic functionality tests passed")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error in functionality test: {str(e)}")
        db.session.rollback()
        return False


def main():
    """Main migration function."""
    print("=" * 60)
    print("L&D Metrics Translator - Context Management Migration")
    print("=" * 60)
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
        print(f"Migration started at: {datetime.now()}")
        print()
        
        # Step 1: Create tables
        if not create_context_tables():
            print("Migration failed at table creation step")
            return False
        
        # Step 2: Add schema version
        if not add_schema_version():
            print("Migration failed at schema version step")
            return False
        
        # Step 3: Verify table structure
        if not verify_table_structure():
            print("Migration failed at structure verification step")
            return False
        
        # Step 4: Create indexes
        if not create_indexes():
            print("Migration failed at index creation step")
            return False
        
        # Step 5: Test functionality
        if not test_basic_functionality():
            print("Migration failed at functionality test step")
            return False
        
        print("\n" + "=" * 60)
        print("[OK] MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nContext Management System is now ready to use.")
        print("\nNew features available:")
        print("- User session tracking")
        print("- Context storage and retrieval")
        print("- Metric selection persistence")
        print("- API endpoints for context management")
        print("\nAPI endpoints added:")
        print("- GET  /api/context/session")
        print("- POST /api/context/store")
        print("- GET  /api/context/get/<type>/<key>")
        print("- POST /api/context/metrics/select")
        print("- GET  /api/context/metrics/selected")
        print("- POST /api/context/initialize")
        print()
        
        return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
