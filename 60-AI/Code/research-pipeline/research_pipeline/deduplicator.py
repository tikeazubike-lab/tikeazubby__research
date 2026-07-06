"""Deduplicator stage — removes duplicate documents.

Deduplication strategies:
- Exact URL match (primary)
- Near-duplicate title match (secondary, configurable threshold)
"""
from __future__ import annotations
from difflib import SequenceMatcher
from .models import NormalizedDocument


def deduplicate(docs: list[NormalizedDocument], title_similarity_threshold: float = 0.85) -> list[NormalizedDocument]:
    """Remove duplicate documents, keeping the highest-scoring representative.

    Args:
        docs: List of normalized documents.
        title_similarity_threshold: Ratio (0-1) above which titles are considered duplicates.

    Returns:
        Deduplicated list, sorted by score descending.
    """
    seen_urls: set[str] = set()
    seen_titles: list[str] = []
    deduped: list[NormalizedDocument] = []

    # Sort by score descending so highest-scoring docs are kept
    sorted_docs = sorted(docs, key=lambda d: d.score, reverse=True)

    for doc in sorted_docs:
        # Exact URL dedup
        if doc.url and doc.url in seen_urls:
            continue
        seen_urls.add(doc.url)

        # Near-duplicate title dedup
        if _is_duplicate_title(doc.title, seen_titles, title_similarity_threshold):
            continue
        seen_titles.append(doc.title)

        deduped.append(doc)

    return deduped


def _is_duplicate_title(title: str, existing_titles: list[str], threshold: float) -> bool:
    """Check if title is a near-duplicate of any existing title."""
    if not title or not existing_titles:
        return False
    title_lower = title.lower().strip()
    for existing in existing_titles:
        existing_lower = existing.lower().strip()
        if title_lower == existing_lower:
            return True
        ratio = SequenceMatcher(None, title_lower, existing_lower).ratio()
        if ratio >= threshold:
            return True
    return False
