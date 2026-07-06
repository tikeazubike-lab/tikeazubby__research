"""Normalizer stage — converts RawDocument -> NormalizedDocument.

Extracts top comment, referenced URLs, standardizes fields.
"""
from __future__ import annotations
import re
from .models import RawDocument, NormalizedDocument


def normalize(raw_docs: list[RawDocument]) -> list[NormalizedDocument]:
    """Convert raw documents to normalized format.

    - Extracts top comment text
    - Collects referenced URLs from top comment
    - Strips excess whitespace
    """
    normalized = []
    for doc in raw_docs:
        # Top comment
        top_comment = None
        referenced_urls: list[str] = []
        for comment in doc.comments:
            if comment.is_top_comment:
                top_comment = comment.body
                referenced_urls = _extract_urls(comment.body) + comment.referenced_urls
                break

        normalized.append(NormalizedDocument(
            title=doc.title,
            url=doc.url,
            source_type=doc.source_type,
            content=_clean(doc.content) if isinstance(doc.content, str) else " ".join(str(c) for c in doc.content),
            score=doc.score,
            subreddit_or_section=doc.subreddit_or_section,
            author=doc.author,
            timestamp=doc.timestamp,
            top_comment=_clean(top_comment) if top_comment else None,
            top_comment_author=None,
            referenced_urls=list(set(referenced_urls)),
            comments=[_clean(c.body) for c in doc.comments if c.body],
            metadata=doc.metadata,
        ))
    return normalized


def _clean(text: str | None) -> str:
    """Strip excess whitespace and control chars."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    return text


_URL_REGEX = re.compile(r"https?://[^\s<>\"']+")


def _extract_urls(text: str) -> list[str]:
    """Extract URLs from text."""
    if not text:
        return []
    return _URL_REGEX.findall(text)
