#!/usr/bin/env python3
"""
Step 2: Paginate SEC Egbuna results using saved Turnstile token.
No browser needed — pure HTTP requests. Runs without Xvfb.
Resumable: reads existing CSV, continues from where it left off.
"""

import csv
import sys
import time
from datetime import datetime
from pathlib import Path
import requests

SCRIPT_DIR = Path(__file__).parent.resolve()
TOKEN_FILE = SCRIPT_DIR / ".sec_token.txt"
OUTPUT_CSV = SCRIPT_DIR.parent.parent / "70-Resources/References/sec-egbuna-full.csv"

API_URL = "https://eportal.sec.gov.ng/api/unmandated-table"
SEARCH = "Egbuna"
PAGE_SIZE = 10
DELAY = 6.0
BREATHER_N = 80
BREATHER_SLEEP = 60.0
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://eportal.sec.gov.ng/non-mandated",
}

def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def main():
    token = TOKEN_FILE.read_text().strip()
    if not token:
        log("FATAL: no token in token file")
        return

    log(f"Token: {len(token)} chars")

    # Count existing rows
    existing = 0
    if OUTPUT_CSV.exists():
        with open(OUTPUT_CSV) as fh:
            existing = sum(1 for _ in fh) - 1
    log(f"Existing rows: {existing}")

    start_page = max(1, existing // PAGE_SIZE + 1)
    log(f"Starting from page {start_page}")

    if not OUTPUT_CSV.exists() or existing == 0:
        with open(OUTPUT_CSV, "w", newline="") as fh:
            csv.writer(fh).writerow(["Account#", "Shareholder", "Company", "Operator"])

    total = existing

    for page in range(start_page, start_page + 10000):
        if page > start_page:
            time.sleep(DELAY)

        params = {
            "pageSize": PAGE_SIZE, "page": page,
            "search": SEARCH, "recaptcha_token": token,
        }
        try:
            resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
        except Exception as e:
            log(f"Page {page}: request error: {type(e).__name__}: {e}")
            time.sleep(30)
            continue

        if resp.status_code == 403:
            log(f"Page {page}: 403 — token expired. Run acquire-token.py again.")
            log(f"Saved {total - existing} rows this run.")
            break
        if resp.status_code == 429:
            log(f"Page {page}: 429 rate limited. Waiting 60s...")
            time.sleep(60)
            continue
        if resp.status_code != 200:
            log(f"Page {page}: HTTP {resp.status_code}")
            time.sleep(10)
            continue

        data = resp.json()
        items = data.get("items") or []
        if not items:
            has_more = data.get("has_more", False)
            log(f"Page {page}: empty — has_more={has_more}")
            if not has_more:
                log("No more pages. Done!")
            break

        with open(OUTPUT_CSV, "a", newline="") as fh:
            w = csv.writer(fh)
            for item in items:
                w.writerow([
                    (item.get("account_number") or "").strip(),
                    (item.get("shareholder_name") or "").strip(),
                    (item.get("company_name") or "").strip(),
                    (item.get("operator_name") or "").strip(),
                ])

        total += len(items)
        if page % 50 == 0 or total % 100 == 0:
            log(f"Page {page:>5d}  +{len(items)}  total={total}")

        if page % BREATHER_N == 0:
            log(f"  Breather {BREATHER_SLEEP}s...")
            time.sleep(BREATHER_SLEEP)

    log(f"\nDone. {total} total rows → {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
