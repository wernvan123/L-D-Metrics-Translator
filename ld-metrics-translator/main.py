import os
from app import create_app, db

# Create the Flask application instance
app = create_app(os.getenv('FLASK_CONFIG') or 'production')

# Initialize database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
