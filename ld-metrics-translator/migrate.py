"""
Database Migration Runner
Usage: python migrate.py [upgrade|downgrade] [version]
"""

import sys
import os
import importlib.util
from flask import Flask
from app import create_app, db

def run_migration(action='upgrade', version=None):
    """Run database migrations."""
    app = create_app()
    
    with app.app_context():
        if action == 'upgrade':
            if version == '001' or version is None:
                print("Running Migration 001...")
                # Load migration module dynamically
                spec = importlib.util.spec_from_file_location(
                    "migration_001", 
                    "migrations/001_rename_neuroscience_concept.py"
                )
                migration_001 = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(migration_001)
                
                success = migration_001.upgrade()
                if success:
                    print("SUCCESS: Migration completed successfully!")
                else:
                    print("ERROR: Migration failed!")
                    return False
        
        elif action == 'downgrade':
            if version == '001' or version is None:
                print("Rolling back Migration 001...")
                # Load migration module dynamically
                spec = importlib.util.spec_from_file_location(
                    "migration_001", 
                    "migrations/001_rename_neuroscience_concept.py"
                )
                migration_001 = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(migration_001)
                
                success = migration_001.downgrade()
                if success:
                    print("SUCCESS: Rollback completed successfully!")
                else:
                    print("ERROR: Rollback failed!")
                    return False
        
        else:
            print("Invalid action. Use 'upgrade' or 'downgrade'")
            return False
    
    return True

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else 'upgrade'
    version = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"Database Migration Runner")
    print(f"Action: {action}")
    if version:
        print(f"Version: {version}")
    print("-" * 40)
    
    success = run_migration(action, version)
    sys.exit(0 if success else 1)
