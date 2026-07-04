#!/usr/bin/env python3
"""
Step 1: Acquire Turnstile token, save to file.
Step 2 (run-sec.sh): Paginate using saved token via requests.
"""

import asyncio, sys
from pathlib import Path
import nodriver as uc

CHROME = str(sorted(
    Path("/home/zubbyik/.cache/ms-playwright").glob("chromium-*/chrome-linux64/chrome"),
    reverse=True,
)[0])
TOKEN_FILE = Path(__file__).parent / ".sec_token.txt"

async def main():
    browser = await uc.start(
        headless=False, browser_executable_path=CHROME,
        browser_args=["--no-sandbox","--disable-dev-shm-usage",
                       "--disable-blink-features=AutomationControlled",
                       "--disable-extensions","--disable-sync",
                       "--no-first-run","--mute-audio"],
        window_size=(800,600),
    )
    try:
        page = await browser.get("https://eportal.sec.gov.ng/non-mandated")
        await asyncio.sleep(12)
        token = await page.evaluate('window.turnstile?.getResponse?.() || ""')
        if token:
            TOKEN_FILE.write_text(token)
            print(f"Token saved: {len(token)} chars → {TOKEN_FILE}")
        else:
            print("FAILED: empty token")
            sys.exit(1)
    finally:
        browser.stop()

asyncio.run(main())
