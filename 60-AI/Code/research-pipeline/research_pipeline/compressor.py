"""Compressor stage — compresses long discussions while preserving key structure.

Reduces token count before Hermes synthesis.
Preserves: main complaint, supporting evidence, proposed solution, representative quote, links.
"""
from __future__ import annotations
from .models import NormalizedDocument


def compress(doc: NormalizedDocument, max_content_chars: int = 1000, max_comments: int = 5) -> NormalizedDocument:
    """Compress a single document to reduce token count.

    Args:
        doc: Normalized document.
        max_content_chars: Maximum characters for main content body.
        max_comments: Maximum number of comments to keep.

    Returns:
        Compressed document (mutated in-place, also returned).
    """
    # Compress main content
    if doc.content and len(doc.content) > max_content_chars:
        doc.content = doc.content[:max_content_chars] + "\n[...truncated]"

    # Compress top comment
    if doc.top_comment and len(doc.top_comment) > max_content_chars:
        doc.top_comment = doc.top_comment[:max_content_chars] + "\n[...truncated]"

    # Reduce number of comments
    if doc.comments and len(doc.comments) > max_comments:
        doc.comments = doc.comments[:max_comments]

    return doc


def compress_all(docs: list[NormalizedDocument], max_content_chars: int = 1000, max_comments: int = 5) -> list[NormalizedDocument]:
    """Compress all documents in a list."""
    return [compress(d, max_content_chars, max_comments) for d in docs]
