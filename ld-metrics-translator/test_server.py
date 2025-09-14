from main import app
from app.models import db

with app.app_context():
    try:
        print('Testing database connection...')
        db.create_all()
        print('Database connection OK')
        
        # Test API routes
        with app.test_client() as client:
            print('Testing API endpoints...')
            
            # Test outcomes endpoint
            response = client.get('/api/outcomes')
            print(f'Outcomes API: {response.status_code}')
            if response.status_code != 200:
                print(f'Error: {response.get_data(as_text=True)}')
            
            # Test types endpoint  
            response = client.get('/api/types')
            print(f'Types API: {response.status_code}')
            if response.status_code != 200:
                print(f'Error: {response.get_data(as_text=True)}')
                
            # Test main page
            response = client.get('/')
            print(f'Main page: {response.status_code}')
            if response.status_code != 200:
                print(f'Error: {response.get_data(as_text=True)}')
                
    except Exception as e:
        import traceback
        print(f'Error: {e}')
        print(traceback.format_exc())
