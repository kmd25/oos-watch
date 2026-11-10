"""Apply the SQL migrations that have not been applied yet, in filename order."""

import os
from pathlib import Path

import psycopg

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

# autocommit=True so each `conn.transaction()` block below is its own real transaction.
with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
    conn.execute(
        """
        create table if not exists schema_migrations (
            filename   text primary key,
            applied_at timestamptz not null default now()
        )
        """
    )
    applied = {row[0] for row in conn.execute("select filename from schema_migrations")}

    pending = [path for path in sorted(MIGRATIONS_DIR.glob("*.sql")) if path.name not in applied]
    for path in pending:
        # The migration and its bookkeeping row succeed or fail together.
        with conn.transaction():
            conn.execute(path.read_text())
            conn.execute("insert into schema_migrations (filename) values (%s)", (path.name,))
        print(f"applied {path.name}")

    if not pending:
        print("nothing to apply")
