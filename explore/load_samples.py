"""Load the saved samples in data/samples/ into the database.

The samples hold rows that have since aged out of FMCSA's data, so run this after
resetting the local database and before the live ingest.

Run from the project root: uv run --env-file .env python -m explore.load_samples
"""

import json
import os
from datetime import date
from pathlib import Path

import psycopg

from ingest import store

SAMPLES_DIR = Path("data/samples")
SAVED_ON = date(2026, 11, 6)  # the day explore/save_samples.py was run


def load(name):
    return json.loads((SAMPLES_DIR / f"{name}.json").read_text())


with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
    with conn.transaction():
        store.add_carrier(conn, os.environ["CARRIER_DOT_NUMBER"])
        store.save(conn, load("inspections"), load("violations"), load("sms"), SAVED_ON)
print("samples loaded")
