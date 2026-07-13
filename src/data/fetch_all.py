"""
Master data ingestion script.
Runs all data fetchers to download/refresh all FDA datasets.

Usage:
    uv run python src/data/fetch_all.py
"""

from pathlib import Path

from fetch_dashboard import main as fetch_dashboard
from fetch_enforcement import main as fetch_enforcement
from fetch_warning_letters import main as fetch_warning_letters

DATA_RAW = Path(__file__).parents[2] / "data" / "raw"


def main():
    print("=" * 60)
    print("FDA Data Ingestion Pipeline")
    print("=" * 60)

    print("\n[1/3] Fetching warning letters (FDA.gov API)...")
    fetch_warning_letters()

    print("\n[2/3] Fetching enforcement/recall data (openFDA bulk)...")
    fetch_enforcement()

    print("\n[3/3] Fetching dashboard datasets (Selenium)...")
    fetch_dashboard()

    print("\n" + "=" * 60)
    print("All data sources refreshed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
