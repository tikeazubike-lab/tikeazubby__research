#!/usr/bin/env python3
"""Check for existing research notes similar to a query.

Uses Jaccard similarity on keyword overlap (not Levenshtein/fuzzy string
matching). Strips stopwords, lowercases, then computes token-set overlap.

Usage:
    python3 check-existing-research.py --query "WhatsApp chatbot complaints" --days 14
    python3 check-existing-research.py --query "upwork frustrations" --threshold 0.4

Exit codes:
    0 — match found (prints matching file path + similarity)
    1 — no match found
    2 — error
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Vault root: two levels up from 60-AI/Code/
VAULT_ROOT = Path(__file__).resolve().parent.parent.parent
RESEARCH_DIR = VAULT_ROOT / "70-Resources" / "Research"

# Minimal English stopwords for keyword extraction
STOPWORDS = frozenset(
    "a an the is are was were be been being have has had do does did "
    "will would shall should may might can could of in to for on with "
    "at by from as into through during before after above below between "
    "and but or nor not so yet both either neither each every all any "
    "few more most other some such no nor too very just about also back "
    "even still how its it my our their them they we he she me him her "
    "what which who whom this that these those i you".split()
)


def tokenize(text: str) -> set[str]:
    """Lowercase, strip stopwords, return token set."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    tokens = set(text.split())
    return tokens - STOPWORDS


def jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity between two token sets."""
    if not a or not b:
        return 0.0
    intersection = a & b
    union = a | b
    return len(intersection) / len(union)


def slugify(text: str) -> str:
    """Turn a query into a filename slug for matching."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s]+", "-", text.strip())
    return text


def parse_date_from_filename(filename: str) -> datetime | None:
    """Extract YYYY-MM-DD from a 'YYYY-MM-DD - slug.md' filename."""
    match = re.match(r"(\d{4}-\d{2}-\d{2})\s*-\s*", filename)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d")
        except ValueError:
            return None
    return None


def extract_query_from_filename(filename: str) -> str:
    """Extract the slug portion after 'YYYY-MM-DD - '."""
    match = re.match(r"\d{4}-\d{2}-\d{2}\s*-\s*(.+)\.md$", filename)
    if match:
        return match.group(1).replace("-", " ")
    return filename.replace(".md", "").replace("-", " ")


def check_existing(
    query: str,
    days: int = 14,
    threshold: float = 0.5,
    research_dir: Path | None = None,
) -> list[dict]:
    """Check for existing research notes similar to query.

    Returns list of matches: [{path, filename, similarity, date, query_extracted}]
    """
    research_dir = research_dir or RESEARCH_DIR
    if not research_dir.exists():
        return []

    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    cutoff = datetime.now() - timedelta(days=days)
    matches = []

    for md_file in sorted(research_dir.glob("*.md")):
        # Date window check
        file_date = parse_date_from_filename(md_file.name)
        if file_date and file_date < cutoff:
            continue  # Skip files older than the window

        # Extract query from filename and compute similarity
        file_query = extract_query_from_filename(md_file.name)
        file_tokens = tokenize(file_query)
        sim = jaccard(query_tokens, file_tokens)

        if sim >= threshold:
            matches.append(
                {
                    "path": str(md_file),
                    "filename": md_file.name,
                    "similarity": round(sim, 3),
                    "date": file_date.isoformat() if file_date else None,
                    "query_extracted": file_query,
                }
            )

    # Sort by similarity descending
    matches.sort(key=lambda m: m["similarity"], reverse=True)
    return matches


def main():
    parser = argparse.ArgumentParser(
        description="Check for existing research notes similar to a query"
    )
    parser.add_argument("--query", required=True, help="Research query to check")
    parser.add_argument(
        "--days",
        type=int,
        default=14,
        help="Only consider notes from the last N days (default: 14)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Jaccard similarity threshold (default: 0.5)",
    )
    parser.add_argument(
        "--research-dir",
        type=str,
        default=None,
        help="Override research directory path",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output as JSON instead of human-readable",
    )

    args = parser.parse_args()
    research_dir = Path(args.research_dir) if args.research_dir else None

    matches = check_existing(
        query=args.query,
        days=args.days,
        threshold=args.threshold,
        research_dir=research_dir,
    )

    if args.json_output:
        print(json.dumps({"query": args.query, "matches": matches}, indent=2))
    else:
        if matches:
            print(f"Found {len(matches)} similar research note(s) for: \"{args.query}\"")
            for m in matches:
                print(f"  [{m['similarity']:.0%}] {m['filename']}")
                print(f"         {m['path']}")
                if m["date"]:
                    print(f"         Date: {m['date']}")
        else:
            print(f"No similar research found for: \"{args.query}\"")

    sys.exit(0 if matches else 1)


if __name__ == "__main__":
    main()
