import os

import requests

URL = "https://data.transportation.gov/resource/fx4q-ay7w.json"
DOT_NUMBER = os.environ["CARRIER_DOT_NUMBER"]

response = requests.get(URL, params={"dot_number": DOT_NUMBER}, timeout=30)
response.raise_for_status()
inspections = response.json()

dates = [row["insp_date"] for row in inspections]
print(f"Inspections: {len(inspections)}")
print(f"Date range: {min(dates)} to {max(dates)}")
print(f"Fields in first row: {len(inspections[0])}")
