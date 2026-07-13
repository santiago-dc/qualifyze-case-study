"""
Master data ingestion script.
Runs all data fetchers to download/refresh all FDA datasets.

Usage:
    uv run python src/data/fetch_all.py

Note: Inspections, Citations, and Published 483s must be downloaded manually
from the FDA Data Dashboard (https://datadashboard.fda.gov/oii/cd/inspections.htm)
because it uses Qlik Sense which requires a browser.
"""

from pathlib import Path

from fetch_enforcement import main as fetch_enforcement
from fetch_warning_letters import main as fetch_warning_letters

DATA_RAW = Path(__file__).parents[2] / "data" / "raw"

MANUAL_FILES = [
    "inspections.xlsx",
    "citations.xlsx",
    "published_483s.xlsx",
]


def check_manual_downloads():
    """Verify that manually downloaded files exist."""
    print("\nChecking manually downloaded files...")
    all_present = True
    for filename in MANUAL_FILES:
        path = DATA_RAW / filename
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            print(f"  ✓ {filename} ({size_mb:.1f} MB)")
        else:
            print(f"  ✗ {filename} — MISSING. Download from https://datadashboard.fda.gov/oii/cd/inspections.htm")
            all_present = False
    return all_present


def main():
    print("=" * 60)
    print("FDA Data Ingestion Pipeline")
    print("=" * 60)

    print("\n[1/3] Fetching warning letters...")
    fetch_warning_letters()

    print("\n[2/3] Fetching enforcement/recall data...")
    fetch_enforcement()

    print("\n[3/3] Checking manual downloads...")
    all_ok = check_manual_downloads()

    print("\n" + "=" * 60)
    if all_ok:
        print("All data sources present. Ready for processing.")
    else:
        print("Some files missing. See above for instructions.")
    print("=" * 60)


if __name__ == "__main__":
    main()
