#!/usr/bin/env python3
"""Fallback research normalizer for when the orchestrator API is unreachable.

Takes raw search results (from stdin as JSON, or from a file) and reshapes
them into the orchestrator API schema so research-note.py works unchanged.

The orchestrator schema:
{
  "session_id": "uuid",
  "query": "string",
  "sources_used": ["reddit", "hackernews", "news"],
  "generated_at": "ISO 8601",
  "summary": {
    "executive_summary": "string",
    "themes": [...],
    "sentiment": {...},
    "pros": [...],
    "cons": [...],
    "notable_quotes": [...],
    "potential_leads": [...],
    "actionable_insights": [...]
  },
  "results": [
    { "source": "string", "title": "string", "url": "string",
      "author": null, "published": null, "score": null,
      "text": null, "summary": null, "tags": [], "metadata": {} }
  ]
}

Usage:
    # Pipe raw results from the agent's websearch output
    echo '[{"title":"...","url":"...","snippet":"..."}]' | \\
        python3 research-fallback.py --query "upwork frustrations"

    # Or pass a JSON file
    python3 research-fallback.py --query "upwork frustrations" \\
        --input raw_results.json

    # Or pass results inline (for agent use)
    python3 research-fallback.py --query "upwork frustrations" \\
        --results '[{"title":"...","url":"..."}]'
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


def infer_platform(url: str) -> str:
    """Infer platform name from URL."""
    url_lower = url.lower()
    if "reddit.com" in url_lower:
        return "reddit"
    if "news.ycombinator.com" in url_lower or "hn.algolia.com" in url_lower:
        return "hackernews"
    if "github.com" in url_lower:
        return "github"
    if "twitter.com" in url_lower or "x.com" in url_lower:
        return "twitter"
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    if "stackoverflow.com" in url_lower or "stackexchange.com" in url_lower:
        return "stackoverflow"
    return "web"


def extract_keywords(text: str, top_n: int = 5) -> list[str]:
    """Extract simple keyword tags from text."""
    stopwords = frozenset(
        "a an the is are was were be been being have has had do does did "
        "will would shall should may might can could of in to for on with "
        "at by from as into through during before after above below between "
        "and but or nor not so yet both either neither each every all any "
        "few more most other some such no nor too very just about also back "
        "even still how its it my our their them they we he she me him her "
        "what which who whom this that these those i you is was are were "
        "has have had been being did does will would could should may might "
        "shall can".split()
    )
    text = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    words = [w for w in text.split() if w not in stopwords and len(w) > 2]
    # Count frequency
    freq: dict[str, int] = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    # Sort by frequency, return top N
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words[:top_n]]


def normalize_result(raw: dict) -> dict:
    """Normalize a single raw search result into the orchestrator result schema."""
    url = raw.get("url", raw.get("link", ""))
    title = raw.get("title", "")
    snippet = raw.get("snippet", raw.get("text", raw.get("description", "")))

    return {
        "source": infer_platform(url),
        "title": title,
        "url": url,
        "author": raw.get("author"),
        "published": raw.get("published", raw.get("date")),
        "score": raw.get("score", raw.get("rank")),
        "text": snippet,
        "summary": raw.get("summary"),
        "tags": extract_keywords(f"{title} {snippet}"),
        "metadata": raw.get("metadata", {}),
    }


def build_sentiment(results: list[dict]) -> dict:
    """Rough sentiment estimate from keyword presence in result text."""
    positive_words = {"great", "excellent", "love", "best", "amazing", "fantastic",
                      "recommend", "helpful", "easy", "good", "reliable", "profitable"}
    negative_words = {"terrible", "awful", "worst", "hate", "scam", "frustrated",
                      "disappointed", "impossible", "broken", "useless", "waste",
                      "nightmare", "horrible", "bad", "difficult", "annoying"}

    pos_count = 0
    neg_count = 0
    total = 0

    for r in results:
        text = (r.get("text", "") or "").lower() + " " + (r.get("title", "") or "").lower()
        words = set(re.findall(r"[a-z]+", text))
        pos_count += len(words & positive_words)
        neg_count += len(words & negative_words)
        total += 1

    total_signals = pos_count + neg_count
    if total_signals == 0:
        return {"positive": 0.33, "negative": 0.33, "neutral": 0.34,
                "notes": "No strong sentiment signals detected."}

    return {
        "positive": round(pos_count / total_signals, 2),
        "negative": round(neg_count / total_signals, 2),
        "neutral": round(max(0, 1 - pos_count / total_signals - neg_count / total_signals), 2),
        "notes": f"Based on keyword analysis of {total} results. "
                 f"{pos_count} positive signals, {neg_count} negative signals.",
    }


def build_themes(results: list[dict]) -> list[dict]:
    """Group results into rough themes by keyword co-occurrence."""
    if not results:
        return []

    # Simple approach: cluster by most common keywords across results
    keyword_results: dict[str, list[str]] = {}
    for r in results:
        tags = r.get("tags", [])
        url = r.get("url", "")
        for tag in tags:
            keyword_results.setdefault(tag, []).append(url)

    # Pick top keywords that appear in 2+ results
    themes = []
    seen_urls: set[str] = set()
    for keyword, urls in sorted(keyword_results.items(),
                                 key=lambda x: len(x[1]), reverse=True):
        unique_urls = [u for u in urls if u not in seen_urls]
        if len(unique_urls) >= 2 and len(themes) < 5:
            themes.append({
                "theme": keyword.capitalize(),
                "description": f"Recurring topic across {len(unique_urls)} sources.",
                "supporting_result_urls": unique_urls[:5],
            })
            seen_urls.update(unique_urls)

    return themes


def build_fallback_response(
    query: str,
    raw_results: list[dict],
    sources_hint: list[str] | None = None,
) -> dict:
    """Build a full orchestrator-schema response from raw search results."""
    results = [normalize_result(r) for r in raw_results]
    sources_used = sources_hint or list({r["source"] for r in results})

    sentiment = build_sentiment(results)
    themes = build_themes(results)

    # Pros/cons extraction
    pros = []
    cons = []
    for r in results:
        text = (r.get("text", "") or "").lower()
        if any(w in text for w in ["great", "love", "recommend", "excellent", "best"]):
            # Extract the sentence containing the positive signal
            for sentence in re.split(r"[.!?\n]", r.get("text", "")):
                if any(w in sentence.lower() for w in ["great", "love", "recommend", "excellent", "best"]):
                    cleaned = sentence.strip()
                    if 10 < len(cleaned) < 150:
                        pros.append(cleaned)
                    break
        if any(w in text for w in ["terrible", "awful", "worst", "hate", "scam", "frustrated"]):
            for sentence in re.split(r"[.!?\n]", r.get("text", "")):
                if any(w in sentence.lower() for w in ["terrible", "awful", "worst", "hate", "scam", "frustrated"]):
                    cleaned = sentence.strip()
                    if 10 < len(cleaned) < 150:
                        cons.append(cleaned)
                    break

    # Deduplicate pros/cons
    pros = list(dict.fromkeys(pros))[:5]
    cons = list(dict.fromkeys(cons))[:5]

    # Notable quotes — use first substantive snippets
    quotes = []
    for r in results[:3]:
        text = r.get("text", "")
        if text and len(text) > 30:
            quotes.append({
                "paraphrase": text[:100].strip(),
                "source_url": r.get("url", ""),
                "source_platform": r.get("source", "web"),
            })

    # Potential leads — results with higher scores or buying signals
    leads = []
    lead_signals = {"price", "cost", "buy", "alternative", "switch", "compare",
                    "recommend", "review", "vs", "versus"}
    for r in results:
        text = (r.get("text", "") or "").lower() + " " + (r.get("title", "") or "").lower()
        if any(s in text for s in lead_signals):
            leads.append({
                "signal": "Buying/comparison intent detected",
                "excerpt_paraphrase": (r.get("text", "") or "")[:100].strip(),
                "source_url": r.get("url", ""),
                "source_platform": r.get("source", "web"),
                "confidence": 0.6,
            })

    # Executive summary
    if results:
        exec_summary = (
            f"Research on \"{query}\" returned {len(results)} results from "
            f"{', '.join(sources_used)}. "
            f"Sentiment: {sentiment['positive']:.0%} positive, "
            f"{sentiment['negative']:.0%} negative. "
            f"{len(themes)} recurring themes identified."
        )
    else:
        exec_summary = f"No results found for \"{query}\"."

    return {
        "session_id": str(uuid.uuid4()),
        "query": query,
        "sources_used": sources_used,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "executive_summary": exec_summary,
            "themes": themes,
            "sentiment": sentiment,
            "pros": pros,
            "cons": cons,
            "notable_quotes": quotes,
            "potential_leads": leads,
            "actionable_insights": [],  # Agent fills this in synthesis
        },
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Fallback research normalizer — reshapes raw results into orchestrator schema"
    )
    parser.add_argument("--query", required=True, help="Research query")
    parser.add_argument("--input", type=str, help="JSON file with raw results")
    parser.add_argument("--results", type=str, help="Inline JSON string of raw results")
    parser.add_argument(
        "--sources",
        type=str,
        help="Comma-separated source hints (e.g., 'reddit,hackernews')",
    )

    args = parser.parse_args()

    # Load raw results from stdin, file, or inline
    if args.results:
        raw_results = json.loads(args.results)
    elif args.input:
        raw_results = json.loads(Path(args.input).read_text())
    else:
        # Read from stdin
        stdin_data = sys.stdin.read().strip()
        if not stdin_data:
            print(json.dumps({"error": "No input provided. Pipe JSON results or use --input/--results."},
                             indent=2))
            sys.exit(2)
        raw_results = json.loads(stdin_data)

    sources_hint = args.sources.split(",") if args.sources else None

    response = build_fallback_response(
        query=args.query,
        raw_results=raw_results,
        sources_hint=sources_hint,
    )

    print(json.dumps(response, indent=2, default=str))


if __name__ == "__main__":
    main()
