"""The HTTP API the dashboard reads from. It only reads the database; ingest does the writing.

Run from the project root: uv run --env-file .env uvicorn api.main:app --reload
"""

import os

import psycopg
from fastapi import Depends, FastAPI
from psycopg.rows import dict_row

from api.auth import get_claims
from ingest.fmcsa import DRIVER_LEVELS, VEHICLE_LEVELS

app = FastAPI(title="OOS Watch")


def get_conn():
    """One database connection per request, closed when the response has been sent."""
    with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row) as conn:
        yield conn


def get_dot_number(claims=Depends(get_claims)):
    """Whose data to show. Depending on get_claims means every endpoint needs a valid login.

    For now every signed-in user sees the carrier named in .env; the next step looks up
    the company that the user's organization belongs to.
    """
    return os.environ["CARRIER_DOT_NUMBER"]


def with_rates(counts):
    """Reshape four counts into driver and vehicle blocks, each with its rate.

    The rate is a fraction (0.25 = 25%), or None when there were no inspections to divide by.
    """

    def block(kind):
        inspections = counts[f"{kind}_inspections"]
        oos = counts[f"{kind}_oos_inspections"]
        return {
            "inspections": inspections,
            "oos_inspections": oos,
            "oos_rate": oos / inspections if inspections else None,
        }

    return {
        "period_start": counts["period_start"],
        "period_end": counts["period_end"],
        "driver": block("driver"),
        "vehicle": block("vehicle"),
    }


@app.get("/whoami")
def whoami(claims=Depends(get_claims)):
    """Who the API thinks is calling: the user and their active organization, if any."""
    # "sub" (subject) is the user's ID. "o" is only present when an organization is active.
    return {"user_id": claims["sub"], "organization_id": claims.get("o", {}).get("id")}


@app.get("/summary")
def summary(conn=Depends(get_conn), dot_number=Depends(get_dot_number)):
    # The carrier's last 24 months, up to today. An inspection can count as a driver
    # inspection, a vehicle inspection, or both, depending on its level.
    carrier = conn.execute(
        """
        select
            (current_date - interval '24 months' + interval '1 day')::date as period_start,
            current_date as period_end,
            count(*) filter (where insp_level_id = any(%(driver_levels)s))
                as driver_inspections,
            count(*) filter (where insp_level_id = any(%(driver_levels)s) and driver_oos_total > 0)
                as driver_oos_inspections,
            count(*) filter (where insp_level_id = any(%(vehicle_levels)s))
                as vehicle_inspections,
            count(*) filter (where insp_level_id = any(%(vehicle_levels)s) and vehicle_oos_total > 0)
                as vehicle_oos_inspections
        from inspections
        where dot_number = %(dot_number)s
          and insp_date > current_date - interval '24 months'
        """,
        {
            "dot_number": dot_number,
            "driver_levels": list(DRIVER_LEVELS),
            "vehicle_levels": list(VEHICLE_LEVELS),
        },
    ).fetchone()

    # The newest nationwide figures; ingest stores one row per period.
    national = conn.execute(
        """
        select period_start, period_end,
               driver_inspections, driver_oos_inspections,
               vehicle_inspections, vehicle_oos_inspections
        from national_averages
        order by period_end desc
        limit 1
        """
    ).fetchone()

    # FMCSA's own published figures for this carrier, as of the day we fetched them.
    sms = conn.execute(
        """
        select fetched_on, insp_total,
               driver_insp_total, driver_oos_insp_total,
               vehicle_insp_total, vehicle_oos_insp_total
        from sms_snapshots
        where dot_number = %(dot_number)s
        order by fetched_on desc
        limit 1
        """,
        {"dot_number": dot_number},
    ).fetchone()

    # How fresh the data is: when ingest last saw this carrier's rows at FMCSA,
    # and the date of the newest inspection we hold.
    freshness = conn.execute(
        """
        select max(last_seen_at) as last_ingest_at,
               max(insp_date) as latest_inspection_date
        from inspections
        where dot_number = %(dot_number)s
        """,
        {"dot_number": dot_number},
    ).fetchone()

    # Crash rows in the same 24 months. One row is one of the carrier's vehicles in a
    # crash, counted the way FMCSA counts them.
    crashes = conn.execute(
        """
        select
            count(*) as crashes,
            count(*) filter (where fatalities > 0) as fatal_crashes,
            count(*) filter (where injuries > 0) as injury_crashes
        from crashes
        where dot_number = %(dot_number)s
          and report_date > current_date - interval '24 months'
        """,
        {"dot_number": dot_number},
    ).fetchone()

    return {
        "carrier": with_rates(carrier),
        "national": with_rates(national) if national else None,
        "sms": sms,
        "crashes": crashes,
        "freshness": freshness,
    }


@app.get("/inspections")
def inspections(conn=Depends(get_conn), dot_number=Depends(get_dot_number)):
    # Every inspection we hold for the carrier, newest first, including ones that have
    # aged out of FMCSA's own data. The left join keeps inspections with no violations.
    return conn.execute(
        """
        select
            i.inspection_id, i.insp_date, i.report_state, i.report_number,
            i.insp_level_id, i.location_desc,
            i.viol_total, i.oos_total, i.driver_oos_total, i.vehicle_oos_total,
            count(v.insp_violation_id) filter (where v.out_of_service) as oos_violation_rows,
            -- FMCSA's total and its own violation rows sometimes disagree; flag those.
            i.oos_total <> count(v.insp_violation_id) filter (where v.out_of_service) as oos_mismatch
        from inspections i
        left join violations v on v.inspection_id = i.inspection_id
        where i.dot_number = %(dot_number)s
        group by i.inspection_id
        order by i.insp_date desc, i.inspection_id desc
        """,
        {"dot_number": dot_number},
    ).fetchall()


@app.get("/violations/top")
def top_violations(conn=Depends(get_conn), dot_number=Depends(get_dot_number)):
    # The carrier's ten most frequent violation codes in the last 24 months (the same
    # window as /summary). Violations have no DOT number or date of their own, so both
    # come from the inspection they belong to.
    return conn.execute(
        """
        select
            v.viol_code,
            max(v.viol_desc) as viol_desc,
            count(*) as violations,
            count(*) filter (where v.out_of_service) as oos_violations,
            count(distinct v.inspection_id) as inspections,
            max(i.insp_date) as latest_date
        from violations v
        join inspections i on i.inspection_id = v.inspection_id
        where i.dot_number = %(dot_number)s
          and i.insp_date > current_date - interval '24 months'
        group by v.viol_code
        order by violations desc, oos_violations desc, v.viol_code
        limit 10
        """,
        {"dot_number": dot_number},
    ).fetchall()


@app.get("/trends")
def trends(conn=Depends(get_conn), dot_number=Depends(get_dot_number)):
    # One row per calendar month, from the carrier's first inspection to this month.
    # generate_series makes the list of months, so a month with no inspections still
    # appears (with zeros) and the chart has no gaps.
    return conn.execute(
        """
        with months as (
            select generate_series(
                date_trunc('month', (select min(insp_date) from inspections
                                     where dot_number = %(dot_number)s)),
                date_trunc('month', current_date),
                interval '1 month'
            )::date as month
        )
        select
            m.month,
            count(i.inspection_id) as inspections,
            coalesce(sum(i.viol_total), 0) as violations,
            count(*) filter (where i.oos_total > 0) as oos_inspections,
            count(*) filter (where i.insp_level_id = any(%(driver_levels)s))
                as driver_inspections,
            count(*) filter (where i.insp_level_id = any(%(driver_levels)s) and i.driver_oos_total > 0)
                as driver_oos_inspections,
            count(*) filter (where i.insp_level_id = any(%(vehicle_levels)s))
                as vehicle_inspections,
            count(*) filter (where i.insp_level_id = any(%(vehicle_levels)s) and i.vehicle_oos_total > 0)
                as vehicle_oos_inspections
        from months m
        left join inspections i
            on i.dot_number = %(dot_number)s
           and i.insp_date >= m.month
           and i.insp_date < m.month + interval '1 month'
        group by m.month
        order by m.month
        """,
        {
            "dot_number": dot_number,
            "driver_levels": list(DRIVER_LEVELS),
            "vehicle_levels": list(VEHICLE_LEVELS),
        },
    ).fetchall()


@app.get("/crashes")
def crashes(conn=Depends(get_conn), dot_number=Depends(get_dot_number)):
    # Every crash row we hold for the carrier, newest first.
    return conn.execute(
        """
        select
            crash_id, report_date, report_time, report_state, city, location,
            fatalities, injuries, tow_away, hazmat_released, federal_recordable,
            vehicles_in_accident,
            -- The same vehicle twice on the same day is probably one crash reported twice.
            -- FMCSA counts both, so we keep both and flag them for the carrier to check.
            vin is not null
                and count(*) over (partition by vin, report_date) > 1 as possible_duplicate
        from crashes
        where dot_number = %(dot_number)s
        order by report_date desc, crash_id desc
        """,
        {"dot_number": dot_number},
    ).fetchall()
