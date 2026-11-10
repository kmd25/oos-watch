"""Tests for the upsert. They need a real Postgres with the migrations applied.

Each test runs inside a transaction that is rolled back, so nothing is left behind.
"""

from datetime import date

import psycopg
import pytest

from ingest import store

DOT = "9999999"
TODAY = date(2026, 11, 10)


def counts(conn):
    return conn.execute(
        """
        select (select count(*) from inspections where dot_number = %(dot)s),
               (select count(*) from violations v
                  join inspections i using (inspection_id) where i.dot_number = %(dot)s),
               (select count(*) from sms_snapshots where dot_number = %(dot)s)
        """,
        {"dot": DOT},
    ).fetchone()


def test_save_stores_every_row(conn, inspections, violations, sms):
    store.add_carrier(conn, DOT)
    store.save(conn, inspections, violations, sms, TODAY)

    assert counts(conn) == (2, 3, 1)


def test_saving_twice_changes_nothing(conn, inspections, violations, sms):
    store.add_carrier(conn, DOT)
    store.add_carrier(conn, DOT)
    store.save(conn, inspections, violations, sms, TODAY)
    store.save(conn, inspections, violations, sms, TODAY)

    assert counts(conn) == (2, 3, 1)


def test_a_changed_row_is_updated_not_duplicated(conn, inspections, violations, sms):
    store.add_carrier(conn, DOT)
    store.save(conn, inspections, violations, sms, TODAY)

    inspections[0]["viol_total"] = "7"
    store.save(conn, inspections, violations, sms, TODAY)

    stored = conn.execute(
        "select viol_total, raw ->> 'viol_total' from inspections where inspection_id = 1"
    ).fetchone()
    assert stored == (7, "7")
    assert counts(conn) == (2, 3, 1)


def test_rows_missing_from_a_later_fetch_are_kept(conn, inspections, violations, sms):
    store.add_carrier(conn, DOT)
    store.save(conn, inspections, violations, sms, TODAY)

    # The source's window moves on: only the newer inspection comes back.
    store.save(conn, inspections[1:], violations[2:], sms, TODAY)

    assert counts(conn) == (2, 3, 1)


def test_a_new_day_adds_a_new_sms_snapshot(conn, inspections, violations, sms):
    store.add_carrier(conn, DOT)
    store.save(conn, inspections, violations, sms, date(2026, 11, 9))
    store.save(conn, inspections, violations, sms, date(2026, 11, 10))

    assert counts(conn) == (2, 3, 2)


def test_violation_without_its_inspection_is_rejected(conn, inspections, violations, sms):
    store.add_carrier(conn, DOT)

    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        store.save(conn, [], violations, sms, TODAY)
