"""Helper to load the fixture CSV as bytes for tests."""
from __future__ import annotations

from pathlib import Path

FIXTURE_PATH = Path(__file__).resolve().parent / "compounds.csv"


def get_fixture_csv_bytes() -> bytes:
    return FIXTURE_PATH.read_bytes()
