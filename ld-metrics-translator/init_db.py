#!/usr/bin/env python3
"""
Database initialization script for L&D Metrics Translator.
This script initializes the database and can seed it with basic or comprehensive data.

Usage:
    python init_db.py                    # Basic seeding (original behavior)
    python init_db.py --comprehensive    # Comprehensive seeding with 20+ metrics
    python init_db.py --help            # Show help
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.database import init_database, seed_basic_data, seed_sample_metrics, get_database_stats
from app.seed_data import DataSeeder
from app.models import AdminUser


def create_default_admin_user():
    """Create a default admin user if none exists."""
    if AdminUser.query.count() == 0:
        print("Creating default admin user...")
        admin = AdminUser(
            username='admin',
            email='admin@example.com',
            is_active=True
        )
        admin.set_password('admin123')  # Default password - should be changed
        db.session.add(admin)
        db.session.commit()
        print("Default admin user created:")
        print("  Username: admin")
        print("  Password: admin123")
        print("  WARNING: Change the default password after first login!")
    else:
        print(f"Admin users already exist ({AdminUser.query.count()} found)")


def main():
    """Initialize the database with basic or comprehensive data."""
    # Parse command line arguments
    comprehensive = False
    if len(sys.argv) > 1:
        if sys.argv[1] == '--comprehensive':
            comprehensive = True
        elif sys.argv[1] == '--help':
            print(__doc__)
            return
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Use --help for usage information")
            return
    
    print("Initializing L&D Metrics Translator Database...")
    
    # Create Flask app
    app = create_app('development')
    
    with app.app_context():
        print("Creating database tables...")
        init_database()
        
        # Create default admin user if none exists
        create_default_admin_user()
        
        if comprehensive:
            print("\n[*] Running comprehensive data seeding...")
            seeder = DataSeeder()
            success = seeder.run_full_seed(force=True)
            if success:
                print("\n[SUCCESS] Comprehensive database initialization complete!")
            else:
                print("\n[ERROR] Comprehensive seeding failed!")
                sys.exit(1)
        else:
            print("Seeding basic data...")
            seed_basic_data()
            
            print("Seeding sample metrics...")
            seed_sample_metrics()
            
            print("\n[SUCCESS] Basic database initialization complete!")
        
        print("\n[INFO] Database Statistics:")
        get_database_stats()
        
        if not comprehensive:
            print("\n[TIP] Use 'python init_db.py --comprehensive' for full sample data")


if __name__ == '__main__':
    main()
