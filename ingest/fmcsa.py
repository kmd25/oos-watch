"""Fetch raw rows from FMCSA's public datasets on data.transportation.gov.

Nothing here cleans or stores data; these functions return rows exactly as the API sends them.
"""

from datetime import timedelta

import requests

BASE_URL = "https://data.transportation.gov/resource"
INSPECTIONS = "fx4q-ay7w"
VIOLATIONS = "876r-jsdb"
SMS = "4y6x-dmck"
CRASHES = "aayw-vxb3"

PAGE_SIZE = 1000  # rows per request; also the API's own default
ID_BATCH_SIZE = 100  # inspection IDs per violations request, to keep the URL short

# Which inspection levels count as a driver inspection and as a vehicle inspection.
# Level 3 is driver-only and level 5 (terminal) is vehicle-only.
# The API's SQL uses these same two tuples, so the rule lives in one place.
DRIVER_LEVELS = (1, 2, 3, 6)
VEHICLE_LEVELS = (1, 2, 5, 6)


def fetch_all(dataset, filters, order):
    """Return every row that matches `filters`, requesting one page at a time."""
    rows = []
    while True:
        # Paging only works with a fixed sort order; otherwise pages can overlap or skip rows.
        params = {**filters, "$order": order, "$limit": PAGE_SIZE, "$offset": len(rows)}
        response = requests.get(f"{BASE_URL}/{dataset}.json", params=params, timeout=30)
        response.raise_for_status()
        page = response.json()
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows


def check_digits(value):
    """DOT numbers will come from sign-up forms, so never pass one on unchecked."""
    if not value.isdigit():
        raise ValueError(f"expected only digits, got {value!r}")


def fetch_inspections(dot_number):
    check_digits(dot_number)
    return fetch_all(INSPECTIONS, {"dot_number": dot_number}, "inspection_id")


def fetch_violations(inspection_ids):
    """The violations dataset has no dot_number, so we ask for them by inspection ID."""
    rows = []
    for start in range(0, len(inspection_ids), ID_BATCH_SIZE):
        batch = inspection_ids[start : start + ID_BATCH_SIZE]
        for inspection_id in batch:
            check_digits(inspection_id)
        id_list = ", ".join(f"'{inspection_id}'" for inspection_id in batch)
        rows.extend(fetch_all(VIOLATIONS, {"$where": f"inspection_id in ({id_list})"}, "insp_violation_id"))
    return rows


def fetch_sms(dot_number):
    check_digits(dot_number)
    return fetch_all(SMS, {"dot_number": dot_number}, "dot_number")


def fetch_crashes(dot_number):
    check_digits(dot_number)
    return fetch_all(CRASHES, {"dot_number": dot_number}, "crash_id")


def last_24_full_months(today):
    """The 24 complete calendar months before `today`: (first day, last day)."""
    start_of_this_month = today.replace(day=1)
    period_start = start_of_this_month.replace(year=start_of_this_month.year - 2)
    period_end = start_of_this_month - timedelta(days=1)
    return period_start, period_end


def count(dataset, where):
    """Ask the API to count matching rows itself, instead of sending them all to us."""
    params = {"$select": "count(*) as n", "$where": where}
    response = requests.get(f"{BASE_URL}/{dataset}.json", params=params, timeout=120)
    response.raise_for_status()
    return int(response.json()[0]["n"])


def quoted(levels):
    """The source stores levels as text, so (1, 2) becomes "'1', '2'" for its query language."""
    return ", ".join(f"'{level}'" for level in levels)


def fetch_national_counts(period_start, period_end):
    """Count every carrier's inspections in the period, and how many had an OOS violation."""
    # insp_date is text in YYYYMMDD form, which sorts the same way as the dates themselves.
    dates = f"insp_date between '{period_start:%Y%m%d}' and '{period_end:%Y%m%d}'"
    driver = f"{dates} and insp_level_id in ({quoted(DRIVER_LEVELS)})"
    vehicle = f"{dates} and insp_level_id in ({quoted(VEHICLE_LEVELS)})"
    return {
        "period_start": period_start,
        "period_end": period_end,
        "driver_inspections": count(INSPECTIONS, driver),
        "driver_oos_inspections": count(INSPECTIONS, f"{driver} and driver_oos_total > '0'"),
        "vehicle_inspections": count(INSPECTIONS, vehicle),
        "vehicle_oos_inspections": count(INSPECTIONS, f"{vehicle} and vehicle_oos_total > '0'"),
    }
