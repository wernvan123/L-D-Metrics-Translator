#!/usr/bin/env python3
"""
Admin setup script for L&D Metrics Translator.
This script sets up the admin interface and creates admin users.

Usage:
    python setup_admin.py                    # Create default admin user
    python setup_admin.py --user USERNAME    # Create specific admin user
    python setup_admin.py --reset            # Reset admin users
"""

import os
import sys
import getpass

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import AdminUser, AuditLog


def create_admin_user(username=None, email=None, password=None):
    """Create a new admin user."""
    if not username:
        username = input("Enter username: ").strip()
    
    if not email:
        email = input("Enter email: ").strip()
    
    if not password:
        password = getpass.getpass("Enter password: ")
        confirm_password = getpass.getpass("Confirm password: ")
        if password != confirm_password:
            print("Passwords do not match!")
            return False
    
    # Check if user already exists
    existing_user = AdminUser.query.filter_by(username=username).first()
    if existing_user:
        print(f"User '{username}' already exists!")
        return False
    
    # Create new admin user
    admin = AdminUser(
        username=username,
        email=email,
        is_active=True
    )
    admin.set_password(password)
    
    try:
        db.session.add(admin)
        db.session.commit()
        print(f"Admin user '{username}' created successfully!")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error creating admin user: {e}")
        return False


def reset_admin_users():
    """Reset all admin users (dangerous operation)."""
    confirm = input("This will delete ALL admin users. Are you sure? (type 'yes' to confirm): ")
    if confirm.lower() != 'yes':
        print("Operation cancelled.")
        return
    
    try:
        # Delete audit logs first (foreign key constraint)
        AuditLog.query.delete()
        AdminUser.query.delete()
        db.session.commit()
        print("All admin users have been deleted.")
        
        # Create new default admin
        create_default_admin()
    except Exception as e:
        db.session.rollback()
        print(f"Error resetting admin users: {e}")


def create_default_admin():
    """Create default admin user."""
    print("Creating default admin user...")
    admin = AdminUser(
        username='admin',
        email='admin@example.com',
        is_active=True
    )
    admin.set_password('admin123')
    
    try:
        db.session.add(admin)
        db.session.commit()
        print("Default admin user created:")
        print("  Username: admin")
        print("  Password: admin123")
        print("  Email: admin@example.com")
        print("  WARNING: Change the default password after first login!")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error creating default admin: {e}")
        return False


def list_admin_users():
    """List all admin users."""
    users = AdminUser.query.all()
    if not users:
        print("No admin users found.")
        return
    
    print(f"\nFound {len(users)} admin user(s):")
    print("-" * 60)
    for user in users:
        status = "Active" if user.is_active else "Inactive"
        last_login = user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else "Never"
        print(f"Username: {user.username}")
        print(f"Email: {user.email}")
        print(f"Status: {status}")
        print(f"Created: {user.created_date.strftime('%Y-%m-%d %H:%M')}")
        print(f"Last Login: {last_login}")
        print("-" * 60)


def main():
    """Main function."""
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help':
            print(__doc__)
            return
        elif sys.argv[1] == '--reset':
            reset_flag = True
        elif sys.argv[1] == '--user' and len(sys.argv) > 2:
            username = sys.argv[2]
        elif sys.argv[1] == '--list':
            list_flag = True
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Use --help for usage information")
            return
    
    print("L&D Metrics Translator - Admin Setup")
    print("=" * 40)
    
    # Create Flask app
    app = create_app('development')
    
    with app.app_context():
        # Ensure tables exist
        db.create_all()
        
        if '--list' in sys.argv:
            list_admin_users()
        elif '--reset' in sys.argv:
            reset_admin_users()
        elif '--user' in sys.argv and len(sys.argv) > 2:
            create_admin_user(username=sys.argv[2])
        else:
            # Default behavior - create admin if none exist
            if AdminUser.query.count() == 0:
                create_default_admin()
            else:
                print(f"Admin users already exist ({AdminUser.query.count()} found)")
                list_admin_users()
                
                choice = input("\nWould you like to create another admin user? (y/n): ").lower()
                if choice == 'y':
                    create_admin_user()


if __name__ == '__main__':
    main()
