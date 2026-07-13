"""
Fetch FDA inspection classification data.

The FDA inspection classification database is available at:
https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/inspection-classification-database

This script fetches the data via the same datatables pattern used for warning letters.
Output: data/raw/inspections.json
"""

import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.fda.gov/datatables/views/ajax"
PAGE_SIZE = 100
OUTPUT_PATH = Path(__file__).parents[2] / "data" / "raw" / "inspections.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}


def discover_view_config(page_url: str) -> dict | None:
    """Extract datatables view config from an FDA page."""
    resp = requests.get(page_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    script_tag = soup.find("script", {"data-drupal-selector": "drupal-settings-json"})
    if not script_tag:
        return None
    settings = json.loads(script_tag.string)
    views = settings.get("views", {}).get("ajaxViews", {})
    if views:
        first_view = list(views.values())[0]
        return first_view
    return None


def fetch_inspection_data() -> list[dict]:
    """Fetch all inspection classification records."""
    page_url = "https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/inspection-classification-database"
    print(f"Discovering view config from {page_url}...")
    view_config = discover_view_config(page_url)

    if not view_config:
        print("ERROR: Could not discover view config")
        return []

    print(f"View: {view_config['view_name']} / {view_config['view_display_id']}")

    params = {
        "_drupal_ajax": "1",
        "_wrapper_format": "drupal_ajax",
        "pager_element": "0",
        "view_name": view_config["view_name"],
        "view_display_id": view_config["view_display_id"],
        "view_path": view_config.get("view_path", ""),
        "view_base_path": view_config.get("view_base_path", ""),
        "iDisplayLength": str(PAGE_SIZE),
    }

    all_records = []
    offset = 0

    # First request
    params["iDisplayStart"] = "0"
    resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    total = data.get("recordsTotal", 0)
    print(f"Total inspection records: {total}")

    # Parse first batch
    for row in data.get("data", []):
        all_records.append(parse_inspection_row(row))
    offset += PAGE_SIZE

    while offset < total:
        params["iDisplayStart"] = str(offset)
        resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        rows = data.get("data", [])
        if not rows:
            break
        for row in rows:
            all_records.append(parse_inspection_row(row))
        offset += PAGE_SIZE
        if offset % 1000 == 0:
            print(f"  Fetched {min(offset, total)}/{total}")
        time.sleep(0.3)

    return all_records


def parse_inspection_row(row: list[str]) -> dict:
    """Parse inspection datatables row into structured dict."""
    record = {}
    fields = [
        "firm_name", "city", "state", "country", "zip_code",
        "inspection_end_date", "classification", "project_area",
        "posted_date", "fei_number"
    ]

    for i, field in enumerate(fields):
        if i < len(row):
            cell = row[i]
            if cell:
                soup = BeautifulSoup(cell, "lxml")
                text = soup.get_text(strip=True)
                if field.endswith("_date") and "datetime" in cell:
                    match = re.search(r'datetime="([^"]+)"', cell)
                    if match:
                        text = match.group(1)[:10]
                record[field] = text
            else:
                record[field] = ""
        else:
            record[field] = ""

    return record


def main():
    print("Fetching FDA inspection classifications...")
    records = fetch_inspection_data()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(records, f, indent=2)
    print(f"Saved {len(records)} inspection records to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
