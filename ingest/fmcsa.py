"""Fetch raw rows from FMCSA's public datasets on data.transportation.gov.

Nothing here cleans or stores data; these functions return rows exactly as the API sends them.
"""

import requests

BASE_URL = "https://data.transportation.gov/resource"
INSPECTIONS = "fx4q-ay7w"
VIOLATIONS = "876r-jsdb"
SMS = "4y6x-dmck"

PAGE_SIZE = 1000  # rows per request; also the API's own default
ID_BATCH_SIZE = 100  # inspection IDs per violations request, to keep the URL short


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
