"""Import knowledge base content from `wernerva_kb.sql` into the app database.

Usage:
    poetry run python scripts/import_wernerva_kb.py --database sqlite:///app.db
"""

import argparse
import re
from pathlib import Path

from sqlalchemy.exc import IntegrityError

from app import create_app, db
from app.models import KnowledgeCategory, KnowledgeResource


INSERT_RESOURCES_RE = re.compile(
    r"INSERT INTO resources \([^\)]+\) VALUES",
    re.IGNORECASE,
)

INSERT_CATEGORIES_RE = re.compile(
    r"INSERT INTO categories \([^\)]+\) VALUES",
    re.IGNORECASE,
)


def parse_row(row_text):
    fields = []
    current = []
    in_string = False
    i = 0
    length = len(row_text)

    while i < length:
        ch = row_text[i]

        if in_string:
            if ch == "'":
                next_char = row_text[i + 1] if i + 1 < length else None
                if next_char == "'":
                    current.append("'")
                    i += 2
                    continue
                in_string = False
                fields.append(''.join(current))
                current = []
            else:
                current.append(ch)
        else:
            if ch == "'":
                in_string = True
            elif ch == ',':
                value = ''.join(current).strip()
                fields.append(None if value.upper() == 'NULL' else value)
                current = []
            else:
                current.append(ch)

        i += 1

    if current:
        value = ''.join(current).strip()
        fields.append(None if value.upper() == 'NULL' else value)

    return fields


def split_row_groups(values_blob):
    rows = []
    current = []
    depth = 0
    in_string = False
    escaped = False

    for ch in values_blob:
        if in_string:
            current.append(ch)
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == "'":
                in_string = False
            continue

        if ch == "'":
            in_string = True
            current.append(ch)
        elif ch == '(':
            depth += 1
            current.append(ch)
        elif ch == ')':
            depth -= 1
            current.append(ch)
            if depth == 0:
                rows.append(''.join(current))
                current = []
        elif depth > 0:
            current.append(ch)

    return rows


def extract_values_blob(sql_text, start_index):
    length = len(sql_text)
    i = start_index
    while i < length and sql_text[i].isspace():
        i += 1

    depth = 0
    in_string = False
    escaped = False

    values_chars = []

    while i < length:
        ch = sql_text[i]
        values_chars.append(ch)

        if in_string:
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == "'":
                in_string = False
        else:
            if ch == "'":
                in_string = True
            elif ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            elif ch == ';' and depth <= 0:
                values_chars.pop()  # remove semicolon
                break
        i += 1

    return ''.join(values_chars)


def parse_insert(sql_text, regex):
    rows = []
    for match in regex.finditer(sql_text):
        values_blob = extract_values_blob(sql_text, match.end())
        for group_text in split_row_groups(values_blob):
            row_text = group_text.strip()
            if not row_text:
                continue
            if row_text[0] == '(' and row_text[-1] == ')':
                row_text = row_text[1:-1]
            rows.append(parse_row(row_text))
    return rows


def load_categories(sql_text):
    categories = {}
    for row in parse_insert(sql_text, INSERT_CATEGORIES_RE):
        if len(row) < 2:
            continue
        cat_id = int(row[0])
        categories[cat_id] = {
            'name': row[1],
            'description': row[2] if len(row) > 2 else None,
        }
    return categories


def determine_tier(admin_notes):
    if not admin_notes:
        return 'tx'
    prefix = admin_notes.strip().upper()
    if prefix.startswith('T1') or prefix.startswith('T2'):
        return 't1t2'
    return 'tx'


def import_resources(sql_text, categories_map):
    total = 0
    resource_rows = parse_insert(sql_text, INSERT_RESOURCES_RE)
    print(f'Found {len(resource_rows)} raw resource rows in SQL dump.')
    for row in resource_rows:
        if len(row) < 10:
            continue
        (
            rid,
            heading,
            content,
            _user_id,
            _timestamp,
            admin_notes,
            ref_id,
            seq_id,
            context,
            status,
            *rest,
        ) = row

        status_val = str(status).strip() if status is not None else None
        if status_val and status_val != '2':
            continue

        tier = determine_tier(admin_notes)

        category_id = None
        if ref_id and str(ref_id).isdigit():
            ref_id_int = int(ref_id)
            if ref_id_int in categories_map:
                category_id = ref_id_int

        resource = KnowledgeResource(
            id=int(rid),
            heading=heading,
            content=content,
            tier=tier,
            tags=admin_notes.strip() if isinstance(admin_notes, str) else admin_notes,
            reference=str(ref_id) if ref_id else None,
            context=str(context) if context else None,
            seq_id=int(seq_id) if seq_id else None,
            category_id=category_id,
        )

        db.session.merge(resource)
        total += 1

    db.session.commit()
    return total


def ensure_categories(categories_map):
    for cat_id, data in categories_map.items():
        db.session.merge(
            KnowledgeCategory(
                id=cat_id,
                name=data['name'],
                description=data.get('description'),
            )
        )
    db.session.commit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--sql-path',
        default='wernerva_kb.sql',
        help='Path to the SQL dump file',
    )
    parser.add_argument(
        '--database',
        default=None,
        help='Override SQLAlchemy database URI (optional)',
    )
    args = parser.parse_args()

    sql_path = Path(args.sql_path)
    if not sql_path.exists():
        raise FileNotFoundError(f'SQL dump not found: {sql_path}')

    sql_text = sql_path.read_text(encoding='utf-8', errors='ignore')

    config_overrides = {}
    if args.database:
        config_overrides['SQLALCHEMY_DATABASE_URI'] = args.database

    app = create_app(config_overrides or 'default')

    with app.app_context():
        categories_map = load_categories(sql_text)
        print(f'Loaded {len(categories_map)} categories from SQL dump.')
        ensure_categories(categories_map)
        try:
            total = import_resources(sql_text, categories_map)
        except IntegrityError as err:
            db.session.rollback()
            raise SystemExit(f'Import failed: {err}')

    print(f'Imported {total} resources into knowledge base tables.')


if __name__ == '__main__':
    main()
