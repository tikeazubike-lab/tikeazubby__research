#!/usr/bin/env python3
"""Generate an Obsidian research note from orchestrator API response JSON.

Reads the structured API response from stdin (or --input) and writes a
formatted Markdown note to 70-Resources/Research/YYYY-MM-DD - {query-slug}.md.

Maps each summary.* field directly to its corresponding note section:
  summary.executive_summary  -> ## Executive Summary
  summary.themes[]           -> ## Recurring Themes
  summary.sentiment          -> ## Sentiment
  summary.pros               -> ## Pros
  summary.cons               -> ## Cons
  summary.notable_quotes[]   -> ## Notable Quotes
  summary.potential_leads[]  -> ## Potential Leads
  summary.actionable_insights-> ## Actionable Insights
  results[]                  -> ## Source Links (grouped by platform)

Usage:
    echo '{json}' | python3 research-note.py --output-dir "70-Resources/Research"
    python3 research-note.py --input response.json --output-dir "70-Resources/Research"
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Vault root: two levels up from 60-AI/Code/
VAULT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT_DIR = VAULT_ROOT / "70-Resources" / "Research"


def slugify(text: str) -> str:
    """Turn a query into a filename-safe slug."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s]+", "-", text.strip())
    return text[:80]  # cap length


def format_yaml_list(items: list[str]) -> str:
    """Format a Python list as a YAML array string."""
    return json.dumps(items)


def render_frontmatter(data: dict) -> str:
    """Render YAML frontmatter."""
    query = data.get("query", "unknown")
    sources = data.get("sources_used", [])
    date_str = data.get("generated_at", datetime.now(timezone.utc).isoformat())
    # Extract just the date
    try:
        date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        date = datetime.now().strftime("%Y-%m-%d")

    # Generate tags from query keywords
    stopwords = {"a", "an", "the", "is", "are", "was", "were", "of", "in",
                 "to", "for", "on", "with", "at", "by", "from", "and", "or",
                 "about", "how", "what", "why", "when", "where"}
    query_tags = [w for w in re.sub(r"[^a-z0-9\s]", "", query.lower()).split()
                  if w not in stopwords and len(w) > 2]
    tags = ["research"] + query_tags[:5]

    lines = [
        "---",
        f"type: research",
        f"date: {date}",
        f'query: "{query}"',
        f"sources_used: {format_yaml_list(sources)}",
        f"tags: {format_yaml_list(tags)}",
        f"status: active",
        "---",
    ]
    return "\n".join(lines)


def render_executive_summary(summary: dict) -> str:
    text = summary.get("executive_summary", "")
    if not text:
        return "## Executive Summary\n\n*No results found for this section.*\n"
    return f"## Executive Summary\n\n{text}\n"


def render_themes(summary: dict) -> str:
    themes = summary.get("themes", [])
    if not themes:
        return "## Recurring Themes\n\n*No results found for this section.*\n"

    lines = ["## Recurring Themes\n"]
    for i, theme in enumerate(themes, 1):
        name = theme.get("theme", f"Theme {i}")
        desc = theme.get("description", "")
        urls = theme.get("supporting_result_urls", [])

        lines.append(f"### {i}. {name}\n")
        if desc:
            lines.append(f"{desc}\n")
        if urls:
            lines.append("**Sources:**\n")
            for url in urls:
                lines.append(f"- [{url}]({url})")
            lines.append("")
    return "\n".join(lines) + "\n"


def render_sentiment(summary: dict) -> str:
    sentiment = summary.get("sentiment", {})
    if not sentiment:
        return "## Sentiment\n\n*No results found for this section.*\n"

    pos = sentiment.get("positive", 0)
    neg = sentiment.get("negative", 0)
    neu = sentiment.get("neutral", 0)
    notes = sentiment.get("notes", "")

    lines = [
        "## Sentiment\n",
        "| Category | Score |",
        "|----------|-------|",
        f"| Positive | {pos:.0%} |",
        f"| Negative | {neg:.0%} |",
        f"| Neutral  | {neu:.0%} |",
        "",
    ]
    if notes:
        lines.append(f"{notes}\n")
    return "\n".join(lines)


def render_pros_cons(summary: dict) -> str:
    pros = summary.get("pros", [])
    cons = summary.get("cons", [])
    if not pros and not cons:
        return ""

    lines = []
    if pros:
        lines.append("## Pros\n")
        for p in pros:
            lines.append(f"- {p}")
        lines.append("")
    if cons:
        lines.append("## Cons\n")
        for c in cons:
            lines.append(f"- {c}")
        lines.append("")
    return "\n".join(lines) + "\n"


def render_notable_quotes(summary: dict) -> str:
    quotes = summary.get("notable_quotes", [])
    if not quotes:
        return "## Notable Quotes\n\n*No results found for this section.*\n"

    lines = ["## Notable Quotes\n"]
    for q in quotes:
        paraphrase = q.get("paraphrase", "")
        source_url = q.get("source_url", "")
        platform = q.get("source_platform", "")

        if paraphrase:
            line = f"- \"{paraphrase}\""
            if source_url:
                line += f" ([{platform}]({source_url}))"
            elif platform:
                line += f" — *{platform}*"
            lines.append(line)
    lines.append("")
    return "\n".join(lines) + "\n"


def render_potential_leads(summary: dict) -> str:
    leads = summary.get("potential_leads", [])
    if not leads:
        return "## Potential Leads\n\n*No results found for this section.*\n"

    lines = ["## Potential Leads\n"]
    for lead in leads:
        signal = lead.get("signal", "")
        excerpt = lead.get("excerpt_paraphrase", "")
        source_url = lead.get("source_url", "")
        platform = lead.get("source_platform", "")
        confidence = lead.get("confidence", 0)

        lines.append(f"### {signal}\n")
        if excerpt:
            lines.append(f"> {excerpt}\n")
        meta_parts = []
        if source_url:
            meta_parts.append(f"Source: [{platform}]({source_url})")
        elif platform:
            meta_parts.append(f"Platform: {platform}")
        if confidence:
            meta_parts.append(f"Confidence: {confidence:.0%}")
        if meta_parts:
            lines.append(f"*{' | '.join(meta_parts)}*\n")
    return "\n".join(lines)


def render_actionable_insights(summary: dict) -> str:
    insights = summary.get("actionable_insights", [])
    if not insights:
        return "## Actionable Insights\n\n*No results found for this section.*\n"

    lines = ["## Actionable Insights\n"]
    for insight in insights:
        lines.append(f"- {insight}")
    lines.append("")
    return "\n".join(lines) + "\n"


def render_source_links(results: list[dict]) -> str:
    """Group results by platform and render as deduplicated source links."""
    if not results:
        return "## Source Links\n\n*No results found for this section.*\n"

    by_platform: dict[str, list[dict]] = defaultdict(list)
    seen_urls: set[str] = set()

    for r in results:
        url = r.get("url", "")
        if url and url not in seen_urls:
            platform = r.get("source", "web")
            by_platform[platform].append(r)
            seen_urls.add(url)

    lines = ["## Source Links\n"]
    for platform in sorted(by_platform.keys()):
        platform_results = by_platform[platform]
        lines.append(f"### {platform.capitalize()}\n")
        for r in platform_results:
            title = r.get("title", "Untitled")
            url = r.get("url", "")
            score = r.get("score")
            score_str = f" (score: {score})" if score else ""
            if url:
                lines.append(f"- [{title}]({url}){score_str}")
            else:
                lines.append(f"- {title}{score_str}")
        lines.append("")
    return "\n".join(lines) + "\n"


def render_related_notes_placeholder() -> str:
    """Placeholder section for auto-linking (done by the agent after note creation)."""
    return "## Related Notes\n\n*Auto-linking pending — will be populated after note creation.*\n"


def generate_note(data: dict) -> str:
    """Generate the full Obsidian note from orchestrator API response."""
    summary = data.get("summary", {})
    results = data.get("results", [])

    sections = [
        render_frontmatter(data),
        "",
        f"# Research: {data.get('query', 'Untitled')}\n",
        render_executive_summary(summary),
        render_themes(summary),
        render_sentiment(summary),
        render_pros_cons(summary),
        render_notable_quotes(summary),
        render_potential_leads(summary),
        render_actionable_insights(summary),
        render_source_links(results),
        render_related_notes_placeholder(),
    ]

    return "\n".join(sections)


def write_note(data: dict, output_dir: Path) -> Path:
    """Generate and write the note. Returns the file path."""
    output_dir.mkdir(parents=True, exist_ok=True)

    query = data.get("query", "unknown")
    date_str = data.get("generated_at", datetime.now(timezone.utc).isoformat())
    try:
        date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        date = datetime.now().strftime("%Y-%m-%d")

    slug = slugify(query)
    filename = f"{date} - {slug}.md"
    filepath = output_dir / filename

    note_content = generate_note(data)
    filepath.write_text(note_content, encoding="utf-8")
    return filepath


def main():
    parser = argparse.ArgumentParser(
        description="Generate Obsidian research note from orchestrator API response"
    )
    parser.add_argument("--input", type=str, help="JSON file with API response")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output directory for the note (default: 70-Resources/Research/)",
    )

    args = parser.parse_args()

    # Load API response
    if args.input:
        data = json.loads(Path(args.input).read_text())
    else:
        stdin_data = sys.stdin.read().strip()
        if not stdin_data:
            print("Error: No input provided. Pipe JSON or use --input.", file=sys.stderr)
            sys.exit(2)
        data = json.loads(stdin_data)

    output_dir = Path(args.output_dir)
    filepath = write_note(data, output_dir)

    # Print the path so the agent can reference it
    print(str(filepath))


if __name__ == "__main__":
    main()
