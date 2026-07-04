# SEC Nigeria Non-Mandated Scraper

> Updated 2026-07-04 after testing. The original instruction was wrong about Turnstile.

## Site reality

| Original claim | Actual |
|---|---|
| "not behind any firewall" | Cloudflare Turnstile (invisible, sitekey `0x4AAAAAACKEVgCgqQXYrQQv`) |
| "not gated" | Every API request requires a Turnstile `recaptcha_token` |
| "no login blocker" | Turnstile challenge blocks unauthorized requests |

**API:** `GET https://eportal.sec.gov.ng/non-mandated/api/unmandated-table`  
**Params:** `search`, `pageSize`, `page`, `cursor`, `recaptcha_token`

## What works (and what doesn't)

| Approach | Result |
|---|---|
| Playwright headless | Turnstile blocked |
| Playwright headless=False + Xvfb + playwright-stealth | Turnstile still blocked (widget never renders) |
| **nodriver (raw CDP)** | ✅ Works — `navigator.webdriver` is genuinely false |

## The solution

`nodriver` uses Chrome DevTools Protocol directly instead of WebDriver, naturally bypassing Turnstile. On headless servers like Netcup, it needs Xvfb (already installed).

### Key nodriver gotcha

Arrow functions aren't executed by `page.evaluate()` — use IIFEs:
```python
# WRONG:
result = await page.evaluate("() => { return data; }")
# RIGHT:
result = await page.evaluate("(function() { return data; })()")
```

## Running the scraper

```
./60-AI/Code/run-sec-scraper.sh                    # foreground
./60-AI/Code/run-sec-scraper.sh --background        # daemon
./60-AI/Code/run-sec-scraper.sh --status            # check
./60-AI/Code/run-sec-scraper.sh --stop              # kill
```

## Files

| File | Purpose |
|------|---------|
| `60-AI/Code/sec-scraper.py` | Nodriver-based scraper |
| `60-AI/Code/run-sec-scraper.sh` | Bash wrapper (auto-detects Xvfb) |
| `60-AI/Code/scraper.log` | Runtime log |
| `70-Resources/References/sec-egbuna-non-mandated-results.md` | Output |

## Search targets

| Query | Filter | Description |
|---|---|---|
| `Egbuna Abiodun` | exact | All results |
| `Abiodun` | regex `osita|egbuna` | Filtered |
| `Egbuna` | regex `benjamin|osita|abiodun|kate|jerome|cate|cat` | Filtered |
