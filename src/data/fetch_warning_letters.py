"""
Fetch all FDA warning letters from the FDA.gov datatables API.
Output: data/raw/warning_letters.json
"""

import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.fda.gov/datatables/views/ajax"
PAGE_SIZE = 100
OUTPUT_PATH = Path(__file__).parents[2] / "data" / "raw" / "warning_letters.json"

PARAMS = {
    "_drupal_ajax": "1",
    "_wrapper_format": "drupal_ajax",
    "pager_element": "0",
    "view_name": "warning_letter_solr_index",
    "view_display_id": "warning_letter_solr_block",
    "view_path": "/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters",
    "length": str(PAGE_SIZE),
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}


def parse_row(row: list[str]) -> dict:
    """Parse a single datatables row (HTML fragments) into structured data."""
    posted_date = ""
    issue_date = ""
    company_name = ""
    letter_url = ""
    issuing_office = ""
    subject = ""

    if row[0]:
        match = re.search(r'datetime="([^"]+)"', row[0])
        if match:
            posted_date = match.group(1)[:10]

    if row[1]:
        match = re.search(r'datetime="([^"]+)"', row[1])
        if match:
            issue_date = match.group(1)[:10]

    if row[2]:
        soup = BeautifulSoup(row[2], "lxml")
        a_tag = soup.find("a")
        if a_tag:
            company_name = a_tag.get_text(strip=True)
            letter_url = a_tag.get("href", "")
            if letter_url and not letter_url.startswith("http"):
                letter_url = "https://www.fda.gov" + letter_url

    if row[3]:
        issuing_office = BeautifulSoup(row[3], "lxml").get_text(strip=True)

    if row[4]:
        subject = BeautifulSoup(row[4], "lxml").get_text(strip=True)

    return {
        "posted_date": posted_date,
        "issue_date": issue_date,
        "company_name": company_name,
        "letter_url": letter_url,
        "issuing_office": issuing_office,
        "subject": subject,
    }


def fetch_all_warning_letters() -> list[dict]:
    """Paginate through the FDA datatables API and collect all warning letters."""
    all_records = []
    offset = 0
    draw = 1

    # First request to get total count
    params = {**PARAMS, "start": "0", "draw": str(draw)}
    resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    total = data.get("recordsTotal", 0)
    print(f"Total warning letters: {total}")

    for row in data.get("data", []):
        all_records.append(parse_row(row))

    offset += PAGE_SIZE
    draw += 1

    while offset < total:
        params = {**PARAMS, "start": str(offset), "draw": str(draw)}
        resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        rows = data.get("data", [])
        if not rows:
            break

        for row in rows:
            all_records.append(parse_row(row))

        offset += PAGE_SIZE
        draw += 1
        if offset % 500 == 0 or offset >= total:
            print(f"  Fetched {min(offset, total)}/{total}")
        time.sleep(0.3)

    return all_records


def main():
    print("Fetching FDA warning letters...")
    records = fetch_all_warning_letters()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(records, f, indent=2)
    print(f"Saved {len(records)} warning letters to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
