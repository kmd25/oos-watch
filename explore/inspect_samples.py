"""Profile the saved samples. Prints shapes and counts, never carrier details."""

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

SAMPLES_DIR = Path("data/samples")

# The only fields whose real values are printed. None of them identify the carrier.
SHOW_VALUES = {
    "inspections": ["insp_level_id", "insp_facility", "post_acc_ind", "transaction_code"],
    "violations": ["out_of_service_indicator", "defect_verification_id"],
}


def load(name):
    return json.loads((SAMPLES_DIR / f"{name}.json").read_text())


def shape(value):
    return re.sub(r"[A-Za-z]+", "A", re.sub(r"\d+", "9", value))[:20]


def block_lengths(value):
    """'20261021 1430' becomes '8 4'."""
    return " ".join(str(len(block)) for block in value.split())


def is_date(value):
    try:
        datetime.strptime(value, "%Y%m%d")
        return True
    except ValueError:
        return False


def is_hhmm(value):
    return len(value) == 4 and value.isdigit() and value[:2] < "24" and value[2:] < "60"


def number(row, field):
    return int(row.get(field, 0))


def profile(name, rows):
    print(f"\n== {name}: {len(rows)} rows")
    for field in sorted({key for row in rows for key in row}):
        values = [row[field] for row in rows if field in row]
        shapes = Counter(shape(value) for value in values).most_common(3)
        print(f"{field:28} present={len(values):3} distinct={len(set(values)):3} {shapes}")
    for field in SHOW_VALUES.get(name, []):
        print(f"values of {field}: {dict(Counter(row.get(field) for row in rows))}")


def check_dates(inspections, violations):
    print("\n== dates and times")
    bad = sum(not is_date(row["insp_date"]) for row in inspections)
    print(f"insp_date not YYYYMMDD: {bad}")
    print(f"change_date block lengths: {dict(Counter(block_lengths(row['change_date']) for row in violations))}")
    print(f"change_date example: {violations[0]['change_date']}")
    for field in ["insp_start_time", "insp_end_time"]:
        bad = sum(not is_hhmm(row[field]) for row in inspections)
        lengths = Counter(len(row[field]) for row in inspections)
        print(f"{field} not HHMM: {bad}, lengths: {dict(lengths)}")


def check_totals(inspections, violations):
    print("\n== totals")
    for total, parts in [
        ("viol_total", ["driver_viol_total", "vehicle_viol_total", "hazmat_viol_total"]),
        ("oos_total", ["driver_oos_total", "vehicle_oos_total", "hazmat_oos_total"]),
    ]:
        bad = sum(number(row, total) != sum(number(row, part) for part in parts) for row in inspections)
        print(f"{total} != sum of parts: {bad} rows")

    oos_rows = Counter(row["inspection_id"] for row in violations if row["out_of_service_indicator"] == "Y")
    bad = sum(number(row, "oos_total") != oos_rows[row["inspection_id"]] for row in inspections)
    print(f"oos_total != violations marked Y: {bad} inspections")
    print(f"total oos_total: {sum(number(row, 'oos_total') for row in inspections)}, violations marked Y: {sum(oos_rows.values())}")

    # The same OOS question, answered from each table. Unit 'D' looks like the driver.
    driver_y = {row["inspection_id"] for row in violations if row["out_of_service_indicator"] == "Y" and row["insp_viol_unit"] == "D"}
    vehicle_y = {row["inspection_id"] for row in violations if row["out_of_service_indicator"] == "Y" and row["insp_viol_unit"] != "D"}
    vehicle_inspected = sum(row["insp_level_id"] in ("1", "2") for row in inspections)
    print(f"driver OOS inspections: totals say {sum(number(row, 'driver_oos_total') > 0 for row in inspections)}, rows say {len(driver_y)}, out of {len(inspections)}")
    print(f"vehicle OOS inspections: totals say {sum(number(row, 'vehicle_oos_total') > 0 for row in inspections)}, rows say {len(vehicle_y)}, out of {vehicle_inspected} at level 1 or 2")


def check_codes(violations):
    print("\n== violation codes")
    mismatches = [row for row in violations if row["viol_code"] != f"{row['part_no']}.{row['part_no_section']}"]
    print(f"viol_code != part_no.part_no_section: {len(mismatches)}")
    print(f"mismatch shapes: {Counter((shape(row['viol_code']), shape(row['part_no_section'])) for row in mismatches).most_common(5)}")

    descriptions = defaultdict(set)
    for row in violations:
        descriptions[row["viol_code"]].add(row["viol_desc"])
    print(f"codes with more than one description: {sum(len(found) > 1 for found in descriptions.values())}")


def check_units(violations):
    print("\n== violation units")
    pairs = Counter((row["insp_viol_unit"], "insp_unit_id" in row) for row in violations)
    print(f"(insp_viol_unit, has insp_unit_id): {dict(pairs)}")


def check_text(name, rows):
    print(f"\n== text noise in {name} (counts only)")
    leading_zeros, noise = Counter(), Counter()
    for row in rows:
        for field, value in row.items():
            if value.isdigit() and len(value) > 1 and value[0] == "0":
                leading_zeros[field] += 1
            if value == "":
                noise[field, "empty"] += 1
            if value != value.strip():
                noise[field, "outer whitespace"] += 1
            if "  " in value:
                noise[field, "double space"] += 1
            if "\\" in value:
                noise[field, "backslash"] += 1
    print(f"leading zeros: {dict(leading_zeros)}")
    print(f"noise: {dict(noise)}")


inspections = load("inspections")
violations = load("violations")
sms = load("sms")

for name, rows in [("inspections", inspections), ("violations", violations), ("sms", sms)]:
    profile(name, rows)
check_dates(inspections, violations)
check_totals(inspections, violations)
check_codes(violations)
check_units(violations)
for name, rows in [("inspections", inspections), ("violations", violations), ("sms", sms)]:
    check_text(name, rows)
