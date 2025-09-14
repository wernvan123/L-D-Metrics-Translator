import os
import sys

# Ensure the inner package is importable and config module resolves
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
PKG = os.path.join(ROOT, 'ld-metrics-translator')
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from app import create_app  # type: ignore
from flask_migrate import upgrade


def main():
    app = create_app('default')
    with app.app_context():
        upgrade()
        print('Database upgraded to head successfully.')


if __name__ == '__main__':
    main()
