#!/usr/bin/env python3
"""
SEC Nigeria — Full "Egbuna" scraper (hybrid: nodriver token + requests API)
Gets fresh Turnstile token, then uses fast HTTP pagination.
On 403, gets fresh token from browser.
Writes CSV incrementally.
"""

import asyncio
import csv
import json
import re
import time
from datetime import datetime
from pathlib import Path

import nodriver as uc
import requests

# ─── Config ───────────────────────────────────────────────────────────────────

BASE_URL = "https://eportal.sec.gov.ng/non-mandated"
API_URL = "https://eportal.sec.gov.ng/api/unmandated-table"
SEARCH_QUERY = "Egbuna"
PAGE_SIZE = 10

SCRIPT_DIR = Path(__file__).parent.resolve()
OUTPUT_CSV = SCRIPT_DIR.parent.parent / "70-Resources/References/sec-egbuna-full.csv"

CHROME = str(sorted(
    Path("/home/zubbyik/.cache/ms-playwright").glob("chromium-*/chrome-linux64/chrome"),
    reverse=True,
)[0])

DELAY_BETWEEN_API_CALLS = 6.0   # conservative: avoid 429
BREATHER_EVERY_N = 60
BREATHER_DELAY = 45.0
TOKEN_EXPIRY_PAGES = 999999  # effectively disabled — only refresh on 403/429
MAX_PAGE_RETRIES = 3
BACKOFF_BASE = 20.0  # seconds to wait after 429

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://eportal.sec.gov.ng/non-mandated",
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def log(msg: str):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


async def acquire_token() -> str:
    """Launch browser, navigate, get Turnstile token."""
    browser = await uc.start(
        headless=False,
        browser_executable_path=CHROME,
        browser_args=[
            "--no-sandbox", "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--disable-extensions", "--disable-sync",
            "--no-first-run", "--disable-default-apps",
            "--renderer-process-limit=1", "--mute-audio",
        ],
        window_size=(800, 600),
    )
    try:
        page = await browser.get(BASE_URL)
        await asyncio.sleep(12)  # longer wait after rate-limiting
        token = await page.evaluate('window.turnstile?.getResponse?.() || ""')
        log(f"  Token: {len(token)} chars")
        return token
    finally:
        browser.stop()


def fetch_page(page_num: int, token: str) -> dict | None:
    """Call API for a single page. Returns JSON or None on failure."""
    params = {
        "pageSize": PAGE_SIZE,
        "page": page_num,
        "search": SEARCH_QUERY,
        "recaptcha_token": token,
    }
    resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
    if resp.status_code == 200:
        return resp.json()
    if resp.status_code == 429:
        log(f"  API page {page_num}: 429 rate limited, waiting {BACKOFF_BASE}s...")
        time.sleep(BACKOFF_BASE)
        return None
    log(f"  API page {page_num}: HTTP {resp.status_code}")
    return None


async def acquire_token_with_retry() -> str:
    """Get token, retrying if initial page load fails."""
    for attempt in range(3):
        token = await acquire_token()
        if token:
            return token
        log(f"  Token attempt {attempt+1} failed, waiting 60s...")
        await asyncio.sleep(60)
    return ""


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main():
    log("=" * 55)
    log("SEC Egbuna Full Scraper (token + API)")
    log(f"Search: '{SEARCH_QUERY}'  →  {OUTPUT_CSV}")
    log("=" * 55)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    # Get initial token
    log("Acquiring Turnstile token...")
    token = await acquire_token_with_retry()
    if not token:
        log("FATAL: could not get token after retries")
        return

    # Initialize or resume CSV
    existing = 0
    if OUTPUT_CSV.exists():
        with open(OUTPUT_CSV) as fh:
            existing = sum(1 for _ in fh) - 1  # minus header
    if existing > 0:
        start_page = (existing // PAGE_SIZE) + 1
        log(f"Resuming from page {start_page} ({existing} rows in CSV)")
    else:
        start_page = 1
        with open(OUTPUT_CSV, "w", newline="") as fh:
            csv.writer(fh).writerow(["Account#", "Shareholder", "Company", "Operator"])

    total = existing
    page_num = start_page - 1
    pages_with_current_token = 0

    while True:
        page_num += 1
        await asyncio.sleep(DELAY_BETWEEN_API_CALLS)

        page_failures = 0
        data = None
        for retry in range(1, MAX_PAGE_RETRIES + 1):
            data = fetch_page(page_num, token)
            if data is not None:
                break
            if retry < MAX_PAGE_RETRIES:
                wait = retry * BACKOFF_BASE
                log(f"  Page {page_num} retry {retry}/{MAX_PAGE_RETRIES}, waiting {wait}s...")
                await asyncio.sleep(wait)
            page_failures = retry

        if data is None:
            # Token expired — get a fresh one
            log(f"  Token likely expired at page {page_num}, refreshing...")
            await asyncio.sleep(BACKOFF_BASE)
            token = await acquire_token_with_retry()
            if not token:
                log(f"FATAL: token refresh failed at page {page_num}")
                break
            pages_with_current_token = 0
            await asyncio.sleep(3)
            data = fetch_page(page_num, token)

        if data is None:
            log(f"Page {page_num}: still failing after token refresh — stopping")
            break

        items = data.get("items") or data.get("data") or []
        if not items:
            log(f"Page {page_num}: empty — done")
            break

        # Write to CSV
        with open(OUTPUT_CSV, "a", newline="") as fh:
            w = csv.writer(fh)
            for item in items:
                acct = (item.get("account_number") or "").strip()
                sh   = (item.get("shareholder_name") or "").strip()
                co   = (item.get("company_name") or "").strip()
                op   = (item.get("operator_name") or "").strip()
                w.writerow([acct, sh, co, op])

        total += len(items)
        pages_with_current_token += 1
        log(f"Page {page_num:>5d}  +{len(items)}  total={total}")

        # Periodic breather
        if page_num % BREATHER_EVERY_N == 0:
            log(f"  Breather {BREATHER_DELAY}s...")
            await asyncio.sleep(BREATHER_DELAY)

        # Proactive token refresh (only if configured with a real limit)
        if TOKEN_EXPIRY_PAGES > 0 and pages_with_current_token >= TOKEN_EXPIRY_PAGES:
            log(f"  Proactive token refresh (every {TOKEN_EXPIRY_PAGES} pages)")
            token = await acquire_token_with_retry()
            if not token:
                log("FATAL: proactive refresh failed")
                break
            pages_with_current_token = 0

        # Check if there are more pages
        has_more = data.get("has_more", True)
        if not items or not has_more:
            log(f"No more records (has_more={has_more}, items={len(items)})")
            break

    log("=" * 55)
    log(f"DONE  {total} records  {page_num} pages  →  {OUTPUT_CSV}")
    log("=" * 55)


if __name__ == "__main__":
    asyncio.run(main())
