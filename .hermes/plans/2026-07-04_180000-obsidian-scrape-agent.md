# Obsidian Zettelkasten — Scrape Agent Plan

> **Project:** Obsidian Zettelkasten vault (personal knowledge management)
> **Agent role:** AI assistant for vault tasks — scraping, synthesis, connection, analysis
> **Current task:** Scrape SEC Nigeria non-mandated portal for Egbuna family holdings

---

## Project Overview

This is an Obsidian Zettelkasten vault at `/home/zubbyik/obsidan_zettlekasten/` following the standard Zettelkasten method:

- **10-Atomic-Notes/** — One idea per note (evergreen)
- **20-Literature/** — Paper/article notes
- **30-MOCs/** — Maps of Content (topic hubs)
- **40-Projects/** — Active projects
- **50-Journal/** — Daily/weekly logs
- **60-AI/** — AI "defense zone" (raw AI output staged here)
- **70-Resources/** — Templates, references, plugin setup
- **90-Archives/** — Completed/inactive items

The vault covers multiple domains: crypto trading, forex/ICT, freelance, lead gen, affiliate marketing, content/media, PhD research, AI/automation, self-hosting/devops, learning.

---

## Current Task: SEC Nigeria Scraper

The `instruction.md` file requests a background scraper for the Nigerian SEC non-mandated portal at `https://eportal.sec.gov.ng/non-mandated` to extract shareholder records for the Egbuna family.

### Requirements
1. **Batch + time-delayed** scraping to avoid IP blocking
2. **Non-blocking background process** (runs independently)
3. **Output:** Markdown file with headers: `Account# | Shareholder | Company | Operator`
4. **Search names and filters:**
   - "Egbuna Abiodun" (exact, alphanumeric only)
   - "Abiodun" (filtered by regex for `osita | egbuna`)
   - "Egbuna" (filtered by `benjamin | osita | abiodun | kate | jerome | cate | cat`)

### Architecture Decision
- **Python + requests + BeautifulSoup** for scraping
- **asyncio + aiohttp** for async HTTP with rate limiting
- **Bash wrapper** to daemonize and log
- **All AI-generated scripts go in `60-AI/Code/`** per AI Defense Zone rules

### File Locations Confirmed

| Artifact | Path |
|----------|------|
| Python scraper | `60-AI/Code/sec-scraper.py` |
| Bash runner | `60-AI/Code/run-sec-scraper.sh` |
| Output markdown data | `70-Resources/References/sec-egbuna-non-mandated-results.md` |
| Future atomic note (if warranted) | `10-Atomic-Notes/` (subfolder TBD after data review) |

---

## Task Breakdown

### ✅ Site Research Complete

**Target:** `https://eportal.sec.gov.ng/non-mandated`

**Findings:**
- **Framework:** Laravel backend + Vue.js SPA (built with Vite)
- **API endpoint:** `GET /api/unmandated-table` — returns paginated JSON
- **Search params:** `search`, `operator_id` (registrar dropdown), `pageSize`, `page`, `cursor`, `recaptcha_token`
- **Security:** Cloudflare Turnstile (invisible mode, sitekey `0x4AAAAAACKEVgCgqQXYrQQv`)
  - **NOTICE:** The `instruction.md` claimed "not behind any firewall / not gated" — this is wrong. Every search request requires a Turnstile token.
  - Turnstile token is fetched on page 1 only; subsequent pages reuse it
  - 15-second timeout for token acquisition
- **Debounce:** 300ms debounce on input before triggering search
- **Pagination:** Cursor-based + page number, configurable page size (5/10/20)
- **Output columns:** `account_number`, `shareholder_name`, `company_name`, `operator_name`

**Implication:** A headless browser (Playwright/Puppeteer) is required to solve the Turnstile challenge. Simple `requests` won't work. The scraper must use a real browser context.

### Task 2: Write the Python scraper (Playwright-based)

**Key insight:** This site has Cloudflare Turnstile protection. A simple `requests`-based scraper won't work. We need Playwright to:
1. Navigate to the page, solve the Turnstile challenge (it's invisible — Playwright handles this in non-headless or with proper stealth)
2. Intercept the XHR calls to `/api/unmandated-table`
3. Search for each name, collect all results
4. Save as markdown with Account# | Shareholder | Company | Operator

**Strategy options:**
- **Option A (Recommended):** Use Playwright to navigate the page, type each search query, wait for the Turnstile to solve, intercept API responses
- **Option B:** Solve Turnstile once via Playwright, extract the token, then use raw HTTP for batched requests (more fragile)
- **Option C:** Capture the Turnstile token from the page, then use `requests` for paginated fetches (fastest but token may expire)

### Task 3: Write the bash runner script
- Save to `60-AI/Code/run-sec-scraper.sh`
- Creates venv, installs deps, runs scraper in background
- Logs to `60-AI/Code/scraper.log`
- Traps signals for clean shutdown

### Task 4: Run the scraper
- Execute in background
- Monitor progress via log
- Deliver results as markdown file

---

## AI Defense Zone Protocol

All AI-generated output (scripts, synthesis, analysis) goes into `60-AI/` first:
- Scripts → `60-AI/Code/`
- AI summaries → `60-AI/Synthesis/`
- AI connections → `60-AI/Connections/`
- AI critiques → `60-AI/Critiques/`

Before any content enters permanent notes (10-Atomic-Notes, 20-Literature, etc.), it must be reviewed and rewritten by the user.

---

## Vault Conventions
- **Frontmatter:** Every note needs YAML frontmatter (type, status, tags)
- **Links:** `[[wikilinks]]` for internal, `[markdown](url)` for external
- **Tags:** `#domain/crypto`, `#type/atomic`, `#status/active`, `#project/epm`
- **Orphan rule:** Every note links to at least 2 other notes
- **One idea per note** — if multiple ideas, split
