"""Tests for the API. They need a real Postgres with the migrations applied.

The app is given the test's own connection, so everything it reads was inserted by the
test and is rolled back afterwards. All data is made up.
"""

import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from api.main import app, get_conn, get_dot_number

DOT = "9999999"


@pytest.fixture
def client(conn):
    conn.row_factory = dict_row
    conn.execute("insert into carriers (dot_number) values (%s)", (DOT,))
    # Swap the app's real dependencies for the test connection and the fake carrier.
    app.dependency_overrides[get_conn] = lambda: conn
    app.dependency_overrides[get_dot_number] = lambda: DOT
    yield TestClient(app)
    app.dependency_overrides.clear()


def add_inspection(conn, inspection_id, age, level, driver_oos=0, vehicle_oos=0, viol_total=0):
    """Insert an inspection dated `age` before today, e.g. '1 month'."""
    conn.execute(
        """
        insert into inspections (
            inspection_id, dot_number, report_state, report_number, insp_date, insp_level_id,
            viol_total, oos_total, driver_viol_total, driver_oos_total,
            vehicle_viol_total, vehicle_oos_total, hazmat_viol_total, hazmat_oos_total, raw
        )
        values (%s, %s, 'TX', 'TEST', current_date - %s::interval, %s,
                %s, %s, 0, %s, 0, %s, 0, 0, '{}')
        """,
        (inspection_id, DOT, age, level, viol_total, driver_oos + vehicle_oos, driver_oos, vehicle_oos),
    )


def test_summary_counts_by_level_and_oos(client, conn):
    add_inspection(conn, 1, "1 month", level=1, vehicle_oos=2)  # driver + vehicle, vehicle OOS
    add_inspection(conn, 2, "2 months", level=2)  # driver + vehicle, clean
    add_inspection(conn, 3, "3 months", level=3, driver_oos=1)  # driver only, driver OOS
    add_inspection(conn, 4, "4 months", level=5)  # vehicle only, clean
    add_inspection(conn, 5, "25 months", level=1, driver_oos=1, vehicle_oos=1)  # too old

    carrier = client.get("/summary").json()["carrier"]

    assert carrier["driver"] == {"inspections": 3, "oos_inspections": 1, "oos_rate": 1 / 3}
    assert carrier["vehicle"] == {"inspections": 3, "oos_inspections": 1, "oos_rate": 1 / 3}


def test_summary_with_no_inspections_has_no_rate(client):
    body = client.get("/summary").json()

    assert body["carrier"]["driver"] == {"inspections": 0, "oos_inspections": 0, "oos_rate": None}
    assert body["sms"] is None
    assert body["crashes"] == {"crashes": 0, "fatal_crashes": 0, "injury_crashes": 0}
    assert body["freshness"] == {"last_ingest_at": None, "latest_inspection_date": None}


def test_summary_returns_newest_national_row_and_sms_snapshot(client, conn):
    # Far-future dates, so these are the newest rows whatever the dev database holds.
    conn.execute(
        """
        insert into national_averages values
            ('2998-12-31', '2997-01-01', 100, 5, 80, 20),
            ('2999-12-31', '2998-01-01', 200, 10, 50, 10)
        """
    )
    conn.execute(
        """
        insert into sms_snapshots (dot_number, fetched_on, insp_total, driver_insp_total,
            driver_oos_insp_total, vehicle_insp_total, vehicle_oos_insp_total, raw)
        values (%(dot)s, '2026-01-01', 1, 1, 0, 1, 0, '{}'),
               (%(dot)s, '2026-02-01', 9, 9, 2, 5, 1, '{}')
        """,
        {"dot": DOT},
    )

    body = client.get("/summary").json()

    assert body["national"]["period_end"] == "2999-12-31"
    assert body["national"]["driver"] == {"inspections": 200, "oos_inspections": 10, "oos_rate": 0.05}
    assert body["national"]["vehicle"]["oos_rate"] == 0.2
    assert body["sms"]["fetched_on"] == "2026-02-01"
    assert body["sms"]["driver_oos_insp_total"] == 2


def add_violation(conn, violation_id, inspection_id, out_of_service, code="393.9"):
    conn.execute(
        """
        insert into violations (insp_violation_id, inspection_id, viol_code, viol_desc,
            insp_viol_unit, out_of_service, raw)
        values (%s, %s, %s, %s, '1', %s, '{}')
        """,
        (violation_id, inspection_id, code, f"Description of {code}", out_of_service),
    )


def test_inspections_are_newest_first_and_include_old_ones(client, conn):
    add_inspection(conn, 1, "30 months", level=1)
    add_inspection(conn, 2, "1 month", level=3)
    add_inspection(conn, 3, "6 months", level=2)

    rows = client.get("/inspections").json()

    assert [row["inspection_id"] for row in rows] == [2, 3, 1]


def test_inspections_flag_an_oos_total_that_disagrees_with_the_violation_rows(client, conn):
    add_inspection(conn, 1, "1 month", level=1, vehicle_oos=1)  # total 1, one OOS row: agrees
    add_violation(conn, 11, 1, out_of_service=True)
    add_violation(conn, 12, 1, out_of_service=False)
    add_inspection(conn, 2, "2 months", level=1)  # total 0, but one OOS row: disagrees
    add_violation(conn, 21, 2, out_of_service=True)
    add_inspection(conn, 3, "3 months", level=3)  # no violations at all: agrees

    rows = {row["inspection_id"]: row for row in client.get("/inspections").json()}

    assert (rows[1]["oos_violation_rows"], rows[1]["oos_mismatch"]) == (1, False)
    assert (rows[2]["oos_violation_rows"], rows[2]["oos_mismatch"]) == (1, True)
    assert (rows[3]["oos_violation_rows"], rows[3]["oos_mismatch"]) == (0, False)


def test_top_violations_are_counted_per_code_most_frequent_first(client, conn):
    add_inspection(conn, 1, "1 month", level=1)
    add_violation(conn, 11, 1, out_of_service=False, code="393.9")
    add_violation(conn, 12, 1, out_of_service=True, code="393.9")
    add_violation(conn, 13, 1, out_of_service=False, code="392.2")
    add_inspection(conn, 2, "5 months", level=1)
    add_violation(conn, 21, 2, out_of_service=False, code="393.9")
    add_inspection(conn, 3, "25 months", level=1)  # too old: must not be counted
    add_violation(conn, 31, 3, out_of_service=True, code="392.2")
    add_violation(conn, 32, 3, out_of_service=True, code="392.2")
    add_violation(conn, 33, 3, out_of_service=True, code="392.2")

    rows = client.get("/violations/top").json()

    assert [row["viol_code"] for row in rows] == ["393.9", "392.2"]
    first = rows[0]
    assert first["viol_desc"] == "Description of 393.9"
    assert (first["violations"], first["oos_violations"], first["inspections"]) == (3, 1, 2)
    assert (rows[1]["violations"], rows[1]["oos_violations"]) == (1, 0)


def test_top_violations_returns_at_most_ten_codes(client, conn):
    add_inspection(conn, 1, "1 month", level=1)
    for number in range(12):
        add_violation(conn, 100 + number, 1, out_of_service=False, code=f"390.{number}")

    assert len(client.get("/violations/top").json()) == 10


def test_trends_has_a_row_for_every_month_including_empty_ones(client, conn):
    add_inspection(conn, 1, "3 months", level=1, vehicle_oos=1, viol_total=4)
    add_inspection(conn, 2, "3 months", level=3, viol_total=1)
    add_inspection(conn, 3, "1 month", level=3, driver_oos=1, viol_total=2)

    rows = client.get("/trends").json()

    # Three months ago, two months ago (empty), last month, this month (empty).
    assert [row["inspections"] for row in rows] == [2, 0, 1, 0]
    assert [row["violations"] for row in rows] == [5, 0, 2, 0]
    assert [row["month"][8:] for row in rows] == ["01"] * 4
    first, empty, last, _ = rows
    assert (first["driver_inspections"], first["driver_oos_inspections"]) == (2, 0)
    assert (first["vehicle_inspections"], first["vehicle_oos_inspections"]) == (1, 1)
    assert (last["driver_oos_inspections"], last["vehicle_inspections"]) == (1, 0)
    assert (empty["driver_inspections"], empty["vehicle_inspections"]) == (0, 0)


def test_trends_is_empty_for_a_carrier_with_no_inspections(client):
    assert client.get("/trends").json() == []


def add_crash(conn, crash_id, age, vin=None, fatalities=0, injuries=0):
    """Insert a crash row dated `age` before today, e.g. '1 month'."""
    conn.execute(
        """
        insert into crashes (crash_id, dot_number, report_state, report_number, report_seq_no,
            report_date, fatalities, injuries, vin, raw)
        values (%s, %s, 'TX', 'TEST', 1, current_date - %s::interval, %s, %s, %s, '{}')
        """,
        (crash_id, DOT, age, fatalities, injuries, vin),
    )


def test_summary_counts_crash_rows_in_the_last_24_months(client, conn):
    add_crash(conn, 1, "1 month", injuries=2)
    add_crash(conn, 2, "5 months")
    add_crash(conn, 3, "6 months", fatalities=1, injuries=1)
    add_crash(conn, 4, "30 months", fatalities=1)  # too old

    crashes = client.get("/summary").json()["crashes"]

    assert crashes == {"crashes": 3, "fatal_crashes": 1, "injury_crashes": 2}


def test_crashes_flag_the_same_vehicle_twice_on_one_day(client, conn):
    add_crash(conn, 1, "30 months", vin="VIN-A")  # old rows are still listed
    add_crash(conn, 2, "2 months", vin="VIN-A")
    add_crash(conn, 3, "2 months", vin="VIN-A")  # same vehicle, same day as crash 2
    add_crash(conn, 4, "2 months", vin="VIN-B")  # same day, different vehicle
    add_crash(conn, 5, "1 month")  # no VIN: never flagged
    add_crash(conn, 6, "1 month")

    rows = client.get("/crashes").json()

    assert [row["crash_id"] for row in rows] == [6, 5, 4, 3, 2, 1]
    assert [row["crash_id"] for row in rows if row["possible_duplicate"]] == [3, 2]
