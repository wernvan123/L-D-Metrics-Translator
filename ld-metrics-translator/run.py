import os
from app import create_app, db
from app.models import Metric, LDOutcome, MetricType

app = create_app(os.getenv('FLASK_CONFIG') or 'default')


@app.shell_context_processor
def make_shell_context():
    """Make database models available in Flask shell."""
    return {
        'db': db,
        'Metric': Metric,
        'LDOutcome': LDOutcome,
        'MetricType': MetricType
    }


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080, use_reloader=False, threaded=True)
