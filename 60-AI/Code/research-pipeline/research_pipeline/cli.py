"""CLI entry point for the research pipeline.

Usage:
    uv run python -m research_pipeline.cli --upwork
    uv run python -m research_pipeline.cli --help
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from .config import load_config, UPWORK_RESEARCH_CONFIG
from .pipeline import run_pipeline


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Research Pipeline — evidence-based research with separation of retrieval and reasoning")
    parser.add_argument("--upwork", action="store_true", help="Run the Upwork freelance research study")
    parser.add_argument("--config", type=str, help="Path to a JSON config file")
    parser.add_argument("--dump", action="store_true", help="Dump results as JSON (for Hermes to consume)")
    parser.add_argument("--output", type=str, default="220-Literature", help="Output directory (vault root relative)")

    args = parser.parse_args()

    if args.upwork:
        config = load_config(UPWORK_RESEARCH_CONFIG)
    elif args.config:
        config = load_config(args.config)
    else:
        parser.print_help()
        sys.exit(1)

    # Run pipeline
    docs_by_query = run_pipeline(config)

    # Output
    if args.dump:
        _dump_json(docs_by_query)
    else:
        _print_summary(docs_by_query)


def _dump_json(docs_by_query: dict):
    """Dump results as JSON to stdout (for Hermes to pipe)."""
    output = {}
    for query, docs in docs_by_query.items():
        output[query] = [
            {
                "title": d.title,
                "url": d.url,
                "source_type": d.source_type.value if hasattr(d.source_type, 'value') else str(d.source_type),
                "score": d.score,
                "subreddit_or_section": d.subreddit_or_section,
                "author": d.author,
                "confidence": d.confidence.value if d.confidence else None,
                "top_comment": d.top_comment[:500] if d.top_comment else None,
                "content_preview": d.content[:300] if d.content else None,
                "comment_count": len(d.comments),
            }
            for d in docs
        ]
    print(json.dumps(output, indent=2, default=str))


def _print_summary(docs_by_query: dict):
    """Print a readable summary for human review."""
    total = sum(len(docs) for docs in docs_by_query.values())
    print(f"\n{'='*60}")
    print(f"RESEARCH SUMMARY — {total} documents across {len(docs_by_query)} queries")
    print(f"{'='*60}")
    for query, docs in docs_by_query.items():
        print(f"\n  [{query}] — {len(docs)} docs")
        for d in docs[:3]:  # Show top 3 per query
            conf = d.confidence.value if d.confidence else "?"
            print(f"    {'{:.2f}'.format(d.score) if isinstance(d.score, (int, float)) else d.score:>5} [{conf.upper():>4}] {d.title[:70]}")
            print(f"            {d.url}")
        if len(docs) > 3:
            print(f"    ... and {len(docs) - 3} more")


if __name__ == "__main__":
    main()
