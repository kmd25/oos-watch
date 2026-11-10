"""Turn raw API rows into typed values that match our tables.

The API sends every value as text and leaves empty fields out of the row entirely.
Fields our tables require are read with row["..."], so a missing one fails loudly.
Optional fields are read with row.get("..."), which gives None (stored as NULL).
"""

from datetime import datetime

TOTAL_FIELDS = [
    "viol_total",
    "oos_total",
    "driver_viol_total",
    "driver_oos_total",
    "vehicle_viol_total",
    "vehicle_oos_total",
    "hazmat_viol_total",
    "hazmat_oos_total",
]

SMS_COUNT_FIELDS = [
    "insp_total",
    "driver_insp_total",
    "driver_oos_insp_total",
    "vehicle_insp_total",
    "vehicle_oos_insp_total",
]

OUT_OF_SERVICE = {"Y": True, "N": False}


def to_int(value):
    return None if value is None else int(value)


def to_date(value):
    """'20261021' -> date(2026, 10, 21)"""
    return None if value is None else datetime.strptime(value, "%Y%m%d").date()


def to_time(value):
    """'1430' -> time(14, 30)"""
    return None if value is None else datetime.strptime(value, "%H%M").time()


def clean_inspection(row):
    return {
        "inspection_id": int(row["inspection_id"]),
        "dot_number": row["dot_number"],
        "report_state": row["report_state"],
        "report_number": row["report_number"],
        "insp_date": to_date(row["insp_date"]),
        "insp_start_time": to_time(row.get("insp_start_time")),
        "insp_end_time": to_time(row.get("insp_end_time")),
        "insp_level_id": int(row["insp_level_id"]),
        "location_desc": row.get("location_desc"),
        "county_code_state": row.get("county_code_state"),
        "post_acc_ind": row.get("post_acc_ind"),
        "gross_comb_veh_wt": to_int(row.get("gross_comb_veh_wt")),
        **{field: int(row[field]) for field in TOTAL_FIELDS},
        "raw": row,
    }


def clean_violation(row):
    return {
        "insp_violation_id": int(row["insp_violation_id"]),
        "inspection_id": int(row["inspection_id"]),
        "seq_no": to_int(row.get("seq_no")),
        "viol_code": row["viol_code"],
        "viol_desc": row.get("viol_desc"),
        "part_no": row.get("part_no"),
        "part_no_section": row.get("part_no_section"),
        "insp_viol_unit": row["insp_viol_unit"],
        "insp_unit_id": to_int(row.get("insp_unit_id")),
        # A value other than Y or N raises KeyError rather than being guessed at.
        "out_of_service": OUT_OF_SERVICE[row["out_of_service_indicator"]],
        "citation_number": row.get("citation_number"),
        "raw": row,
    }


def clean_sms(row, fetched_on):
    """The SMS dataset has no date of its own, so the caller supplies the fetch date."""
    return {
        "dot_number": row["dot_number"],
        "fetched_on": fetched_on,
        **{field: to_int(row.get(field)) for field in SMS_COUNT_FIELDS},
        "raw": row,
    }


def dedupe(rows, key):
    """Keep one row per key. If a key repeats, the later row wins."""
    return list({row[key]: row for row in rows}.values())
