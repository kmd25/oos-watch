"""Write rows to Postgres.

Safe to run again and again: a row is inserted if its key is new and updated if it
already exists. Nothing is ever deleted, so rows that age out of FMCSA's data stay here.
"""

from psycopg import sql
from psycopg.types.json import Jsonb

from ingest import clean


def add_carrier(conn, dot_number):
    conn.execute("insert into carriers (dot_number) values (%s) on conflict do nothing", (dot_number,))


def upsert(conn, table, key_columns, rows, track_last_seen):
    """Insert `rows` into `table`; where a row with the same key exists, update it instead."""
    if not rows:
        return
    columns = list(rows[0])

    # "excluded" is Postgres's name for the row we tried to insert.
    updates = [
        sql.SQL("{0} = excluded.{0}").format(sql.Identifier(column))
        for column in columns
        if column not in key_columns
    ]
    if track_last_seen:
        updates.append(sql.SQL("last_seen_at = now()"))

    # Table and column names are built with sql.Identifier, values are sent separately
    # as placeholders, so nothing in a row can change the meaning of the query.
    query = sql.SQL("insert into {} ({}) values ({}) on conflict ({}) do update set {}").format(
        sql.Identifier(table),
        sql.SQL(", ").join(map(sql.Identifier, columns)),
        sql.SQL(", ").join(map(sql.Placeholder, columns)),
        sql.SQL(", ").join(map(sql.Identifier, key_columns)),
        sql.SQL(", ").join(updates),
    )
    # Jsonb() tells the driver to send the raw dict as JSON.
    params = [{**row, "raw": Jsonb(row["raw"])} for row in rows]
    with conn.cursor() as cursor:
        cursor.executemany(query, params)


def save(conn, inspections, violations, sms, fetched_on):
    """Clean and store one carrier's raw rows. The carrier must already be in `carriers`."""
    # Inspections go first: every violation must point at an inspection that exists.
    upsert(
        conn,
        "inspections",
        ["inspection_id"],
        clean.dedupe([clean.clean_inspection(row) for row in inspections], "inspection_id"),
        track_last_seen=True,
    )
    upsert(
        conn,
        "violations",
        ["insp_violation_id"],
        clean.dedupe([clean.clean_violation(row) for row in violations], "insp_violation_id"),
        track_last_seen=True,
    )
    upsert(
        conn,
        "sms_snapshots",
        ["dot_number", "fetched_on"],
        [clean.clean_sms(row, fetched_on) for row in sms],
        track_last_seen=False,
    )
