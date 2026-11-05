import json
import os
from pathlib import Path

import requests

BASE_URL = "https://data.transportation.gov/resource"
INSPECTIONS = "fx4q-ay7w"
VIOLATIONS = "876r-jsdb"
SMS = "4y6x-dmck"

DOT_NUMBER = os.environ["CARRIER_DOT_NUMBER"]
SAMPLES_DIR = Path("data/samples")


def fetch(dataset, params):
    response = requests.get(f"{BASE_URL}/{dataset}.json", params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def save(name, rows):
    path = SAMPLES_DIR / f"{name}.json"
    path.write_text(json.dumps(rows, indent=2))
    print(f"{path}: {len(rows)} rows")


SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

inspections = fetch(INSPECTIONS, {"dot_number": DOT_NUMBER})
save("inspections", inspections)

# Violations have no dot_number field, so we look them up by inspection ID.
ids = ", ".join(f"'{row['inspection_id']}'" for row in inspections)
violations = fetch(VIOLATIONS, {"$where": f"inspection_id in ({ids})"})
save("violations", violations)

sms = fetch(SMS, {"dot_number": DOT_NUMBER})
save("sms", sms)
