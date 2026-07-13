"""
Fetch FDA enforcement/recall data from openFDA bulk downloads.
Downloads drug, device, and food enforcement datasets.
Output: data/raw/{drug,device,food}-enforcement-0001-of-0001.json
"""

import zipfile
from io import BytesIO
from pathlib import Path

import requests

OUTPUT_DIR = Path(__file__).parents[2] / "data" / "raw"

ENDPOINTS = {
    "drug": "https://download.open.fda.gov/drug/enforcement/drug-enforcement-0001-of-0001.json.zip",
    "device": "https://download.open.fda.gov/device/enforcement/device-enforcement-0001-of-0001.json.zip",
    "food": "https://download.open.fda.gov/food/enforcement/food-enforcement-0001-of-0001.json.zip",
}


def download_and_extract(name: str, url: str) -> None:
    """Download a zip file and extract its contents."""
    print(f"  Downloading {name} enforcement...")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()

    with zipfile.ZipFile(BytesIO(resp.content)) as zf:
        zf.extractall(OUTPUT_DIR)

    expected_file = OUTPUT_DIR / f"{name}-enforcement-0001-of-0001.json"
    if expected_file.exists():
        size_mb = expected_file.stat().st_size / (1024 * 1024)
        print(f"  ✓ {name}: {size_mb:.1f} MB")
    else:
        print(f"  ✗ {name}: file not found after extraction")


def main():
    print("Fetching FDA enforcement/recall data...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for name, url in ENDPOINTS.items():
        download_and_extract(name, url)

    print("Done.")


if __name__ == "__main__":
    main()
