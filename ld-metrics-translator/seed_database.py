#!/usr/bin/env python3
"""
Command-line interface for seeding the L&D Metrics Translator database.

Usage:
    python seed_database.py              # Interactive seeding
    python seed_database.py --force      # Force reseed without prompting
    python seed_database.py --help       # Show help
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.seed_data import DataSeeder


def main():
    """Main CLI function."""
    print("[*] L&D Metrics Translator Database Seeder")
    print("===========================================")
    
    # Parse command line arguments
    force = False
    if len(sys.argv) > 1:
        if sys.argv[1] == '--force':
            force = True
            print("[*] Force mode enabled - will clear existing data")
        elif sys.argv[1] == '--help':
            print(__doc__)
            return
        else:
            print(f"[ERROR] Unknown argument: {sys.argv[1]}")
            print("Use --help for usage information")
            return
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        # Initialize and run seeder
        seeder = DataSeeder()
        success = seeder.run_full_seed(force=force)
        
        if success:
            print("\n[SUCCESS] Database seeding completed successfully!")
            print("\nNext steps:")
            print("1. Start the application: python run.py")
            print("2. Open your browser to: http://localhost:5000")
            print("3. Explore the comprehensive L&D metrics data!")
        else:
            print("\n[ERROR] Database seeding failed or was cancelled.")
            sys.exit(1)


if __name__ == '__main__':
    main()
