"""
Fetch FDA Data Dashboard datasets using Selenium (headless Chrome).

These datasets require JavaScript execution (Qlik Sense) and cannot be
downloaded with simple HTTP requests.

Downloads:
- Entire Inspections Dataset → inspections.xlsx
- Entire Citations Dataset → citations.xlsx
- Entire Published 483s Dataset → published_483s.xlsx

Usage:
    uv run python src/data/fetch_dashboard.py

Requirements:
    - Google Chrome installed
    - selenium and webdriver-manager (in pyproject.toml)
"""

import glob
import shutil
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

OUTPUT_DIR = Path(__file__).parents[2] / "data" / "raw"
DASHBOARD_URL = "https://datadashboard.fda.gov/oii/cd/inspections.htm"

DATASETS = [
    ("exp-dt1", "inspections.xlsx"),
    ("exp-dt3", "citations.xlsx"),
    ("exp-dt5", "published_483s.xlsx"),
]


def create_driver(download_dir: str) -> webdriver.Chrome:
    """Create a headless Chrome driver configured for downloads."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option("prefs", {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
    })

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd(
        "Page.setDownloadBehavior",
        {"behavior": "allow", "downloadPath": download_dir},
    )
    return driver


def download_by_id(driver, btn_id: str, output_name: str, download_dir: str, timeout: int = 120) -> bool:
    """Click a download button via JS and wait for the file."""
    for f in glob.glob(f"{download_dir}/*"):
        Path(f).unlink()

    driver.execute_script(f'document.getElementById("{btn_id}").click();')
    time.sleep(3)

    for _ in range(timeout // 2):
        files = [f for f in glob.glob(f"{download_dir}/*") if not f.endswith(".crdownload")]
        if files:
            dest = OUTPUT_DIR / output_name
            shutil.move(files[0], dest)
            size_mb = dest.stat().st_size / (1024 * 1024)
            print(f"  ✓ {output_name} ({size_mb:.1f} MB)")
            return True
        time.sleep(2)

    print(f"  ✗ {output_name} — download timed out after {timeout}s")
    return False


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    download_dir = str(OUTPUT_DIR / "_tmp_downloads")
    Path(download_dir).mkdir(parents=True, exist_ok=True)

    print("Starting headless Chrome...")
    driver = create_driver(download_dir)

    try:
        print(f"Loading {DASHBOARD_URL}...")
        driver.get(DASHBOARD_URL)
        time.sleep(20)
        print(f"Page loaded: {driver.title}")

        for i, (btn_id, filename) in enumerate(DATASETS, 1):
            print(f"\n[{i}/{len(DATASETS)}] Downloading {filename}...")
            download_by_id(driver, btn_id, filename, download_dir)

    finally:
        driver.quit()
        shutil.rmtree(download_dir, ignore_errors=True)

    print("\nDone.")


if __name__ == "__main__":
    main()
