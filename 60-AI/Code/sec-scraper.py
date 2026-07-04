#!/usr/bin/env python3
"""
SEC Nigeria Non-Mandated Dividends Scraper

Scrapes https://eportal.sec.gov.ng/non-mandated for Egbuna family members.

Strategy: Use nodriver (raw CDP) which naturally bypasses Cloudflare Turnstile.
Playwright failed because Turnstile detects WebDriver protocol even with stealth.

Usage:
    uv run sec-scraper.py

Output: ../70-Resources/References/sec-egbuna-non-mandated-results.md
"""

import asyncio
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import nodriver as uc

# ─── Configuration ────────────────────────────────────────────────────────────

BASE_URL = "https://eportal.sec.gov.ng/non-mandated"

SCRIPT_DIR = Path(__file__).parent.resolve()
VAULT_ROOT = SCRIPT_DIR.parent.parent
OUTPUT_PATH = VAULT_ROOT / "70-Resources/References/sec-egbuna-non-mandated-results.md"
LOG_PATH = SCRIPT_DIR / "scraper.log"

SEARCHES = [
    {"name": "Egbuna Abiodun", "query": "Egbuna Abiodun", "filter_type": "exact", "pattern": None},
    {"name": "Abiodun filtered", "query": "Abiodun", "filter_type": "regex",
     "pattern": re.compile(r"osita|egbuna", re.IGNORECASE)},
    {"name": "Egbuna filtered", "query": "Egbuna", "filter_type": "regex",
     "pattern": re.compile(r"benjamin|osita|abiodun|kate|jerome|cate|cat", re.IGNORECASE)},
]

DELAY_BETWEEN_SEARCHES = 3.0
DELAY_BETWEEN_PAGES = 1.5
MAX_RETRIES = 2

# ─── Logging ──────────────────────────────────────────────────────────────────

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")

# ─── Scraper ──────────────────────────────────────────────────────────────────

class SECScraper:
    def __init__(self):
        self.all_results: list[dict] = []
        self.search_round = 0
        self.browser = None
        self.chrome_path = self._find_chrome()

    @staticmethod
    def _find_chrome():
        candidates = sorted(
            Path("/home/zubbyik/.cache/ms-playwright").glob("chromium-*/chrome-linux64/chrome"),
            reverse=True,
        )
        if candidates:
            return str(candidates[0])
        return None

    async def run(self):
        log("=" * 60)
        log("SEC Non-Mandated Scraper starting (nodriver)")
        log("=" * 60)

        if not self.chrome_path:
            log("❌ No chromium binary found. Run: playwright install chromium")
            return

        log(f"Using chromium: {self.chrome_path}")
        log("Launching browser...")

        self.browser = await uc.start(
            headless=False,
            browser_executable_path=self.chrome_path,
            browser_args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
            window_size=(1280, 800),
        )

        try:
            page = await self.browser.get(BASE_URL)
            await asyncio.sleep(8)
            log("Page loaded.")

            for search_cfg in SEARCHES:
                await self._execute_search(page, search_cfg)
                await asyncio.sleep(DELAY_BETWEEN_SEARCHES)

        finally:
            self.browser.stop()

        self._deduplicate()
        self._write_markdown()

        log("=" * 60)
        log(f"Done. {len(self.all_results)} unique results.")
        log(f"Output: {OUTPUT_PATH}")
        log("=" * 60)

    async def _execute_search(self, page, search_cfg):
        self.search_round += 1
        query = search_cfg["query"]
        log(f"\n--- Search {self.search_round}: \"{query}\" ---")

        for attempt in range(1, MAX_RETRIES + 1):
            all_items = await self._do_search(page, query, attempt)
            if all_items is not None:
                break
            # Retry: reload page
            if attempt < MAX_RETRIES:
                log("  Reloading page for retry...")
                page = await self.browser.get(BASE_URL)
                await asyncio.sleep(6)
        else:
            log(f"  ❌ Failed after {MAX_RETRIES} attempts")
            return

        if not all_items:
            log("  No results found")
            return

        log(f"  Page 1: {len(all_items)} results")

        # Paginate
        page_num = 1
        while True:
            try:
                next_btn = await page.query_selector("button:has-text('Next')")
                if not next_btn:
                    break
                # Check if disabled
                disabled = await page.evaluate(
                    '(function() { var b = document.querySelector("button:has-text(\'Next\')"); return b && (b.disabled || b.classList.contains("disabled") || b.getAttribute("aria-disabled") === "true"); })()'
                )
                if disabled:
                    break
            except Exception:
                break

            page_num += 1
            await asyncio.sleep(DELAY_BETWEEN_PAGES)
            log(f"  Fetching page {page_num}...")
            await next_btn.click()

            # Wait for new rows to load
            new_rows = await self._wait_for_results(page)
            if not new_rows:
                break
            log(f"  Page {page_num}: {len(new_rows)} results")
            all_items.extend(new_rows)

        # Apply regex filter
        if search_cfg["filter_type"] == "regex" and search_cfg["pattern"]:
            before = len(all_items)
            all_items = [r for r in all_items if search_cfg["pattern"].search(r.get("shareholder", ""))]
            log(f"  Regex filter: {before} -> {len(all_items)}")

        for r in all_items:
            r["_search"] = search_cfg["name"]
            r["_found_by"] = search_cfg["query"]

        self.all_results.extend(all_items)
        log(f"  ✅ Added {len(all_items)} results")

    async def _do_search(self, page, query, attempt):
        """Type query, wait for Turnstile to solve, return first page results."""
        inp = await page.query_selector('input[placeholder*="Search"]')
        if not inp:
            log("  ⚠️  Search input not found")
            return None

        # Clear existing text
        await inp.click()
        await asyncio.sleep(0.3)
        # Triple-click to select all, then delete
        await inp.click()
        await asyncio.sleep(0.1)
        await inp.click()
        await asyncio.sleep(0.1)
        await inp.send_keys("\b" * 100)
        await asyncio.sleep(0.2)

        # Type query character by character
        log(f"  Typing query (attempt {attempt})...")
        await inp.send_keys(query)
        await asyncio.sleep(0.5)

        # Press Enter to submit
        await inp.send_keys("\n")

        log(f"  Waiting for Turnstile + results...")
        return await self._wait_for_results(page)

    async def _wait_for_results(self, page, timeout=30):
        """Poll until results (or Turnstile error, or empty table) appear."""
        for poll_sec in range(timeout):
            await asyncio.sleep(1)
            td = await page.evaluate(
                'document.querySelector("tbody tr td")?.textContent?.trim() || ""'
            )
            if not td:
                continue
            if "recaptcha" in td.lower() or "required" in td.lower():
                log(f"  ⚠️  Turnstile error: \"{td[:60]}...\"")
                return None
            if "no results" in td.lower():
                log("  No matching records on server")
                return []
            if "loading" in td.lower():
                continue
            if "enter your name" in td.lower():
                continue
            # We have actual data
            log(f"  ✅ Results after {poll_sec+1}s")
            return await self._extract_rows(page)
        log("  ⚠️  Timed out waiting for results")
        return None

    async def _extract_rows(self, page) -> list[dict]:
        import json
        result = await page.evaluate("""
            (function() {
                const rows = document.querySelectorAll('tbody tr');
                const results = [];
                for (const row of rows) {
                    const cells = row.querySelectorAll('td');
                    if (cells.length >= 4) {
                        const account = cells[0].textContent.trim();
                        const shareholder = cells[1].textContent.trim();
                        const company = cells[2].textContent.trim();
                        const opLink = cells[3].querySelector('a');
                        const operator = opLink
                            ? opLink.textContent.trim()
                            : cells[3].textContent.trim();
                        if (account || shareholder) {
                            results.push({
                                account_number: account,
                                shareholder: shareholder,
                                company: company,
                                operator: operator,
                            });
                        }
                    }
                }
                return JSON.stringify(results);
            })()
        """)
        return json.loads(result) if result else []

    def _deduplicate(self):
        seen = set()
        unique = []
        for r in self.all_results:
            key = (r.get("account_number", ""), r.get("company", ""))
            if key not in seen and key != ("", ""):
                seen.add(key)
                unique.append(r)
        self.all_results = unique

    def _write_markdown(self):
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "---",
            "type: reference",
            "status: active",
            "tags: [reference, sec-ng, dividends, egbuna, research]",
            "source: https://eportal.sec.gov.ng/non-mandated",
            f"scraped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "---",
            "",
            "# SEC Nigeria — Non-Mandated Dividends: Egbuna Family",
            "",
            f"> Scraped from [SEC Non-Mandated Portal]({BASE_URL})",
            f"> **Total records:** {len(self.all_results)}",
            "",
            "## Search Coverage",
            "",
            "| Search Query | Filter | Results |",
            "|-------------|--------|---------|",
        ]
        for s in SEARCHES:
            count = sum(1 for r in self.all_results if r.get("_found_by") == s["query"])
            lines.append(f"| `{s['query']}` | {s.get('filter_type','exact')} | {count} |")
        lines.append("")

        by_sh = defaultdict(list)
        for r in sorted(self.all_results, key=lambda x: (x.get("shareholder","").lower(), x.get("company","").lower())):
            by_sh[r.get("shareholder","Unknown")].append(r)

        lines.append("## Records by Shareholder")
        for shareholder in sorted(by_sh.keys()):
            records = by_sh[shareholder]
            lines.append(f"\n### {shareholder} ({len(records)} holdings)\n")
            lines.append("| Account # | Company | Operator |")
            lines.append("|-----------|---------|----------|")
            for r in records:
                lines.append(f"| {r.get('account_number','—')} | {r.get('company','—')} | {r.get('operator','—')} |")

        lines.append("\n## Full Results (Flat)\n")
        lines.append("| Account # | Shareholder | Company | Operator |")
        lines.append("|-----------|-------------|---------|----------|")
        for r in sorted(self.all_results, key=lambda x: (x.get("shareholder","").lower(), x.get("company","").lower())):
            lines.append(f"| {r.get('account_number','—')} | {r.get('shareholder','—')} | {r.get('company','—')} | {r.get('operator','—')} |")

        lines.append("")
        lines.append("---")
        lines.append(f"_Scraped on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_")

        content = "\n".join(lines) + "\n"
        OUTPUT_PATH.write_text(content)
        log(f"Written {len(self.all_results)} records to {OUTPUT_PATH}")


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    LOG_PATH.write_text("")
    scraper = SECScraper()
    asyncio.run(scraper.run())
