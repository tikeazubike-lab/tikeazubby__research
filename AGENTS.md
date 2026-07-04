# AGENTS.md

## Critical: Read `.hermes/` plans first

Before executing any task described in `instruction.md` or similar files, read the plan in `.hermes/plans/`. The plan contains verified research that may contradict the instruction file. In particular:

- **`instruction.md` may be wrong about site accessibility.** The `.hermes/` plan discovered that `eportal.sec.gov.ng` has Cloudflare Turnstile protection despite the instruction claiming it is "not behind any firewall." Always verify claims from `instruction.md` against the actual site.

## This is an Obsidian vault, not a software project

- No `package.json`, no `pyproject.toml`, no build/lint/test commands.
- Python deps use `uv` (`uv venv`, `uv pip install`, `uv run`).
- The existing scraper venv is at `60-AI/Code/.venv/`.

## AI Defense Zone

All AI-generated code, scripts, synthesis, and output **must** go into `60-AI/` subdirectories:

| Content | Target |
|---------|--------|
| Scripts/tools | `60-AI/Code/` |
| Summaries/analysis | `60-AI/Synthesis/` |
| Connections | `60-AI/Connections/` |
| Critiques | `60-AI/Critiques/` |

Never write AI-generated content directly into `10-Atomic-Notes/`, `20-Literature/`, `30-MOCs/`, or `40-Projects/` — those are for human-curated permanent notes only.

## Why the SEC scraper failed (and what actually works)

### What was tried and failed

1. **Playwright headless=True** → Turnstile blocked (expected)
2. **Playwright headless=False + Xvfb + playwright-stealth** → Turnstile STILL blocked. Even with `navigator.webdriver=false`, the Turnstile widget never renders. Detection happens at a lower level than navigator flags.
3. **Playwright + undetected-playwright** → API mismatch, stealth broken.

### What actually works: nodriver

**`nodriver`** (raw Chrome DevTools Protocol) naturally bypasses Turnstile because it doesn't use WebDriver at all — `navigator.webdriver` is genuinely `false`. On headless servers, it needs Xvfb for the virtual display.

The fixed scraper is at `60-AI/Code/sec-scraper.py`. Dependencies: `nodriver`, `requests`.

### Critical nodriver gotcha: evaluate must use IIFE

In Playwright, `page.evaluate("() => { ... return x; }")` executes the arrow function. In nodriver, it returns the function object without executing it. You MUST use an IIFE:

```python
# WRONG (returns the function, not the result):
result = await page.evaluate("() => { return data; }")

# RIGHT (executes and returns the result):
result = await page.evaluate("(function() { return data; })()")
```

### How to run the scraper

```
# One-time: install nodriver in the venv
source 60-AI/Code/.venv/bin/activate
uv pip install nodriver requests

# Need Chromium binary (already installed via Playwright):
# ls ~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome

# Xvfb is already installed on this server. The bash runner auto-detects it.
./60-AI/Code/run-sec-scraper.sh                    # foreground
./60-AI/Code/run-sec-scraper.sh --background        # daemon
./60-AI/Code/run-sec-scraper.sh --status            # check
./60-AI/Code/run-sec-scraper.sh --stop              # kill
```

## Vault conventions (Obsidian)

- **Links:** `[[wikilinks]]` for internal notes, `[text](url)` for external.
- **Frontmatter:** Every note needs YAML frontmatter with `type`, `status`, and `tags`.
- **File naming:** `YYYY-MM-DD - Title` for journal/dated notes, `Title` for evergreen.
- **Tags format:** `#domain/area`, `#type/note-type`, `#status/active`, `#project/name`.
- **Templates:** Located at `70-Resources/Templates/` — use `TEMPLATE-Atomic-Note.md`, `TEMPLATE-Literature-Note.md`, etc.
- **New notes default to** `00-Inbox/` then get processed into the appropriate permanent folder.
- **Orphan rule:** Every permanent note must link to at least 2 other notes.

## Key files for task context

| File | Purpose |
|------|---------|
| `.hermes/plans/` | Agent task plans with verified research |
| `instruction.md` | User-provided task instructions (may be inaccurate) |
| `README.md` | Vault overview, domain MOCs, conventions |
| `Implementation-Roadmap.md` | Vault setup and workflow phases |
