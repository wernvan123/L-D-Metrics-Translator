from main import app
from app.models import db, LDOutcome, MetricType

with app.app_context():
    try:
        outcomes_count = LDOutcome.query.count()
        types_count = MetricType.query.count()
        print(f'Outcomes: {outcomes_count}')
        print(f'MetricTypes: {types_count}')
        
        if outcomes_count == 0:
            print('No outcomes found - need to seed database')
        if types_count == 0:
            print('No metric types found - need to seed database')
            
    except Exception as e:
        print(f'Database error: {e}')
