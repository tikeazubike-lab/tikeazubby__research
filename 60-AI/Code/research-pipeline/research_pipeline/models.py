"""Data models for the research pipeline.

RawDocument — raw output from a retriever (before normalization)
NormalizedDocument — standardized document after normalization
Comment — a single comment on a thread
SourceType — enum for data sources
ConfidenceLevel — enum for evidence confidence
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SourceType(Enum):
    REDDIT = "reddit"
    HACKER_NEWS = "hacker_news"
    GITHUB = "github"
    DOCUMENTATION = "documentation"
    BLOG = "blog"


class ConfidenceLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Comment:
    """A single comment on a thread or discussion."""
    id: str
    author: str = ""
    body: str = ""
    score: int = 0
    is_top_comment: bool = False
    referenced_urls: list[str] = field(default_factory=list)


@dataclass
class RawDocument:
    """Raw output from a retriever, before normalization.

    Each instance represents one thread/discussion/repo found by a search query.
    Comments are fetched separately via fetch_comments().
    """
    source_type: SourceType
    source_id: str
    title: str
    url: str
    score: int = 0
    subreddit_or_section: str | None = None
    author: str | None = None
    timestamp: str | None = None
    content: str | list[str] = ""
    comments: list[Comment] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedDocument:
    """Standardized document after normalization stage.

    Fields extracted and standardized from RawDocument for downstream processing.
    """
    title: str
    url: str
    source_type: SourceType
    content: str = ""
    score: int = 0
    subreddit_or_section: str | None = None
    author: str | None = None
    timestamp: str | None = None
    top_comment: str | None = None
    top_comment_author: str | None = None
    referenced_urls: list[str] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)
    major_complaint: str | None = None
    evidence_presented: str | None = None
    proposed_solution: str | None = None
    overall_sentiment: str | None = None
    confidence: ConfidenceLevel | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
