"""Fetch every carrier's data from FMCSA and store it. Meant to run once a day.

Run from the project root: uv run --env-file .env python -m ingest.run
"""

import os
from datetime import date

import psycopg

from ingest import fmcsa, store

with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
    # Local convenience: make sure the carrier named in .env is being tracked.
    seed = os.environ.get("CARRIER_DOT_NUMBER")
    if seed:
        store.add_carrier(conn, seed)

    carriers = [row[0] for row in conn.execute("select dot_number from carriers order by dot_number")]
    for position, dot_number in enumerate(carriers, start=1):
        inspections = fmcsa.fetch_inspections(dot_number)
        violations = fmcsa.fetch_violations([row["inspection_id"] for row in inspections])
        sms = fmcsa.fetch_sms(dot_number)

        # One carrier's rows are stored together or not at all.
        with conn.transaction():
            store.save(conn, inspections, violations, sms, date.today())

        # Never print the DOT number: CI logs for a public repo are public.
        print(
            f"carrier {position} of {len(carriers)}: "
            f"{len(inspections)} inspections, {len(violations)} violations, {len(sms)} SMS rows"
        )

    # Nationwide figures for comparison. Refreshed on every run because inspections
    # keep arriving for weeks after they happen.
    period_start, period_end = fmcsa.last_24_full_months(date.today())
    national = fmcsa.fetch_national_counts(period_start, period_end)
    store.save_national(conn, national)
    print(
        f"national {period_start} to {period_end}: "
        f"driver {national['driver_oos_inspections']} of {national['driver_inspections']}, "
        f"vehicle {national['vehicle_oos_inspections']} of {national['vehicle_inspections']}"
    )
