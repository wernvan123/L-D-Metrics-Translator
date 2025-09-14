import sqlite3
from textwrap import indent

DB_PATH = r"ld-metrics-translator/app.db"


def main():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    print("Database:", DB_PATH)
    print("\n== Tables ==")
    tables = cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    for name, sql in tables:
        print(f"- {name}")
        print(indent(sql or '', '    '))

    # Try to guess framework-related tables
    candidates = [
        'frameworks','framework','learning_framework','framework_model','models','taxonomies','taxonomy','dimension','dimensions','category','categories'
    ]
    print("\n== Candidate tables overview ==")
    for t in candidates:
        try:
            cols = cur.execute(f"PRAGMA table_info({t})").fetchall()
        except sqlite3.Error:
            cols = []
        if not cols:
            continue
        print(f"\nTable {t} columns:")
        for c in cols:
            # c tuple: (cid, name, type, notnull, dflt_value, pk)
            print(" -", tuple(c))
        try:
            cnt = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print("Row count:", cnt)
            sample = cur.execute(f"SELECT * FROM {t} LIMIT 5").fetchall()
            if sample:
                # print first row keys and values
                print("Sample row keys:", list(sample[0].keys()))
                for r in sample:
                    print("  ", dict(r))
        except sqlite3.Error as e:
            print("Query error on", t, e)

    con.close()


if __name__ == "__main__":
    main()
