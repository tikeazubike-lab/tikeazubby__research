"""Evidence Ranker stage — ranks and classifies evidence quality.

Uses heuristic signals to assess confidence in each document.
Ranker flags, does NOT decide — final classification is done by Hermes (LLM).
"""
from __future__ import annotations
from .models import NormalizedDocument, ConfidenceLevel


def rank(docs: list[NormalizedDocument]) -> list[NormalizedDocument]:
    """Rank documents by evidence quality.

    Assigns a ConfidenceLevel based on heuristic signals:
    - HIGH: first-hand experience, substantial content, high engagement
    - MEDIUM: reasonable discussion with some specifics
    - LOW: short, vague, promotional, or very low engagement

    Returns the same list with confidence field populated, sorted by quality.
    """
    for doc in docs:
        doc.confidence = _assess_confidence(doc)

    # Sort: high first, then medium, then low
    order = {
        ConfidenceLevel.HIGH.value: 0,
        ConfidenceLevel.MEDIUM.value: 1,
        ConfidenceLevel.LOW.value: 2,
    }
    docs.sort(key=lambda d: order.get(d.confidence.value if d.confidence else "low", 2))
    return docs


def _assess_confidence(doc: NormalizedDocument) -> ConfidenceLevel:
    """Heuristic confidence assessment."""
    signals = _collect_signals(doc)
    score = sum(signals.values())

    if score >= 4:
        return ConfidenceLevel.HIGH
    elif score >= 2:
        return ConfidenceLevel.MEDIUM
    else:
        return ConfidenceLevel.LOW


def _collect_signals(doc: NormalizedDocument) -> dict[str, int]:
    """Collect quality signals as binary (0/1) indicators."""
    signals = {
        "has_content": 1 if len(doc.content) > 200 else 0,
        "has_top_comment": 1 if doc.top_comment and len(doc.top_comment) > 50 else 0,
        "high_score": 1 if doc.score >= 10 else 0,
        "has_multiple_comments": 1 if len(doc.comments) >= 3 else 0,
        "has_referenced_urls": 1 if doc.referenced_urls else 0,
        "has_author": 1 if doc.author else 0,
    }
    return signals
