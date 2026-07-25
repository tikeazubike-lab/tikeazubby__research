---
name: obsidian-research
description: >
  Research assistant for Obsidian vault. Use when the user asks to
  "research X", "find leads on X", "investigate X", "look into X",
  or wants web research structured as a vault note. Also triggers on
  explicit "/research" commands. Do NOT use for casual topic mentions,
  quick questions, or when the user is just discussing a subject.
---

## What I Do

Run structured web research and save results as an Obsidian note with
deduplication, auto-linking, and consistent formatting.

## When to Use

**Trigger on:**
- "research this for me"
- "find leads on X"
- "investigate X"
- "look into X and summarize"
- "/research {query}"

**Do NOT trigger on:**
- Casual mentions of a topic
- Quick factual questions
- When the user is already discussing something and just wants info

## Workflow

### Step 1: Check for existing similar research

Run the dedup checker:

```bash
python3 60-AI/Code/check-existing-research.py --query "{query}" --days 14
```

If a match is found (Jaccard similarity ≥ 0.5), ask the user:
- Append an `## Update — {today}` section to the existing note?
- Or create a new note anyway?

### Step 2: Run research

**IMPORTANT: Try the orchestrator API first, but it likely doesn't exist
yet. Build and test the fallback path so the skill isn't blocked.**

**Option A — Orchestrator API (preferred, if reachable):**

```bash
curl -s -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "{query}", "limit": 20}'
```

If `localhost:8000` is unreachable (connection refused / timeout),
fall through to Option B.

**Option B — Fallback (direct web search / MCP tools):**

Use `websearch` and any connected MCP tools to gather results.
Then run the fallback normalizer to reshape raw results into the
orchestrator schema shape:

```bash
python3 60-AI/Code/research-fallback.py --query "{query}"
```

This approximates the orchestrator schema so `research-note.py`
works unchanged. The fallback path should produce JSON matching
the same contract (see API Schema below) so switching to the real
API later is a drop-in swap, not a rewrite.

### Step 3: Generate the note

Pipe the JSON result to the note generator:

```bash
echo '{json_result}' | python3 60-AI/Code/research-note.py \
  --output-dir "70-Resources/Research"
```

The script handles:
- YAML frontmatter (date, query, sources_used, tags, type, status)
- Section mapping from schema fields
- Deduplication of source URLs
- Filename: `YYYY-MM-DD - {query-slug}.md`

### Step 4: Auto-link to existing vault notes

After the note is written, scan the vault for notes sharing tags
or keywords with the research query. Append `[[wikilinks]]` to a
`## Related Notes` section.

Use `grep` or `glob` to find notes with matching tags from the
frontmatter, then add links manually if the script didn't already.

### Step 5: Report back

Tell the user:
- Path of the created/updated note
- Number of sources found
- Whether dedup matched an existing note
- Any notable leads found

## API Schema (Orchestrator Contract)

The `/research` endpoint returns this structure. Build against this
contract — map each `summary.*` field directly to its note section.

```json
POST /research
{ "query": "string", "limit": 20 }

Response:
{
  "session_id": "uuid",
  "query": "string",
  "sources_used": ["reddit", "hackernews", "news"],
  "generated_at": "ISO 8601 datetime",
  "summary": {
    "executive_summary": "string",
    "themes": [
      { "theme": "string", "description": "string",
        "supporting_result_urls": ["url"] }
    ],
    "sentiment": { "positive": 0.0, "negative": 0.0, "neutral": 0.0,
                    "notes": "string" },
    "pros": ["string"],
    "cons": ["string"],
    "notable_quotes": [
      { "paraphrase": "string", "source_url": "string",
        "source_platform": "string" }
    ],
    "potential_leads": [
      { "signal": "string", "excerpt_paraphrase": "string",
        "source_url": "string", "source_platform": "string",
        "confidence": 0.0 }
    ],
    "actionable_insights": ["string"]
  },
  "results": [
    { "source": "string", "title": "string", "url": "string",
      "author": "string|null", "published": "ISO8601|null",
      "score": "float|null", "text": "string|null",
      "summary": "string|null", "tags": ["string"], "metadata": {} }
  ]
}
```

### Section Mapping

| Schema field | Note section |
|---|---|
| `summary.executive_summary` | `## Executive Summary` |
| `summary.themes[]` | `## Recurring Themes` — each theme gets a heading + description, `supporting_result_urls` become source links |
| `summary.sentiment` | `## Sentiment` — table with positive/negative/neutral percentages, notes as prose |
| `summary.pros` | `## Pros` — bullet list |
| `summary.cons` | `## Cons` — bullet list |
| `summary.notable_quotes[]` | `## Notable Quotes` — paraphrase (≤15 words) with source link |
| `summary.potential_leads[]` | `## Potential Leads` — signal, excerpt paraphrase, source, confidence score |
| `summary.actionable_insights` | `## Actionable Insights` — bullet list |
| `results[]` | `## Source Links` — deduplicated, grouped by platform |

## Output Format

The generated note follows this structure:

```yaml
---
type: research
date: YYYY-MM-DD
query: "original query string"
sources_used: [reddit, hackernews, news]
tags: [research, topic1, topic2]
status: active
---
```

### Sections (in order)

1. `## Executive Summary` — from `summary.executive_summary`
2. `## Recurring Themes` — from `summary.themes[]`
   - Each theme gets a heading + description
   - `supporting_result_urls` become source links
3. `## Sentiment` — from `summary.sentiment`
   - Table with positive/negative/neutral percentages
   - Notes field as prose
4. `## Pros` — from `summary.pros[]`
5. `## Cons` — from `summary.cons[]`
6. `## Notable Quotes` — from `summary.notable_quotes[]`
   - Paraphrase only (≤15 words), with source link
   - No verbatim quotes over ~15 words (respect copyright)
7. `## Potential Leads` — from `summary.potential_leads[]`
   - Signal, excerpt paraphrase, source, confidence score
   - Tagged with buying/comparison intent signals
8. `## Actionable Insights` — from `summary.actionable_insights[]`
9. `## Source Links` — deduplicated, grouped by platform
10. `## Related Notes` — auto-linked wikilinks to vault notes

## Configuration

| Setting | Default | Override via |
|---------|---------|--------------|
| Output folder | `70-Resources/Research/` | `--output-dir` flag |
| Dedup window | 14 days | `--days` flag |
| Dedup threshold | 0.5 Jaccard | `--threshold` flag |
| Orchestrator URL | `http://localhost:8000/research` | `--api-url` flag |
| Results limit | 20 | `--limit` flag |

## Source Hints

If the user provides source hints (e.g., "reddit only", "leads-focused"),
pass them to the API or fallback:

```bash
# API
curl -s -X POST http://localhost:8000/research \
  -d '{"query": "{query}", "limit": 20, "sources": ["reddit"]}'

# Fallback
python3 60-AI/Code/research-fallback.py --query "{query}" --sources reddit
```

## Anti-Fabrication Rule

Every claim in the generated note must trace to an actual search result.
If the orchestrator or fallback returns no results for a section, leave
that section empty with a note: "No results found for this section."
Never generate placeholder or fabricated content.
