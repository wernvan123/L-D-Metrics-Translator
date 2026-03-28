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
    host = os.getenv('FLASK_HOST', '127.0.0.1')
    try:
        port = int(os.getenv('FLASK_PORT', '8080'))
    except Exception:
        port = 8080
    app.run(debug=True, host=host, port=port, use_reloader=False, threaded=True)
