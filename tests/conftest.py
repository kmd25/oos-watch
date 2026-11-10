"""Shared test helpers. pytest loads this file automatically.

The fixture files are made up. Real carrier data must never be committed.
"""

import json
import os
from pathlib import Path

import psycopg
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIXTURES_DIR / f"{name}.json").read_text())


@pytest.fixture
def inspections():
    return load("inspections")


@pytest.fixture
def violations():
    return load("violations")


@pytest.fixture
def sms():
    return load("sms")


@pytest.fixture
def conn():
    """A database connection whose changes are thrown away after each test."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL is not set")
    with psycopg.connect(url) as connection:
        yield connection
        connection.rollback()
