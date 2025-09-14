import os
import sys

# Ensure we can import the inner Flask app package
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
PKG = os.path.join(ROOT, 'ld-metrics-translator')
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from app import create_app, db  # type: ignore
from sqlalchemy import text


def column_exists(conn, table_name: str, column_name: str) -> bool:
    if conn.dialect.name == 'sqlite':
        res = conn.execute(text(f"PRAGMA table_info('{table_name}')")).fetchall()
        cols = {row[1] for row in res}
        return column_name in cols
    else:
        # generic information_schema check
        query = text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = :table
              AND column_name = :col
            LIMIT 1
            """
        )
        return conn.execute(query, {"table": table_name, "col": column_name}).fetchone() is not None


def add_column(conn, table: str, ddl: str):
    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def main():
    app = create_app('default')
    with app.app_context():
        with db.engine.connect() as conn:
            # Add identifier_type if missing
            if not column_exists(conn, 'metrics', 'identifier_type'):
                add_column(conn, 'metrics', 'identifier_type VARCHAR(20)')
                print('Added metrics.identifier_type')
            else:
                print('metrics.identifier_type already exists')
            # Add driver_chain if missing
            if not column_exists(conn, 'metrics', 'driver_chain'):
                add_column(conn, 'metrics', 'driver_chain TEXT')
                print('Added metrics.driver_chain')
            else:
                print('metrics.driver_chain already exists')


if __name__ == '__main__':
    main()
