"""Configuration loader and presets for research runs.

ResearchConfig — dataclass holding all configuration for a single research run.
load_config() — parse config from dict or JSON file.
UPWORK_RESEARCH_CONFIG — preset for the first Upwork freelance study.
"""
from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import SourceType


@dataclass
class ResearchConfig:
    """Configuration for a single research run.

    date_from / date_to — ISO date strings for filtering results.
    Default date_from is '2025-06-01' (no results before June 2025).
    """
    research_task: str
    search_queries: list[str]
    sources: list[SourceType]
    max_threads_per_query: int = 10
    max_comments_per_thread: int = 20
    cache_dir: str = ".research_cache"
    output_dir: str = "20-Literature"
    date_from: str = "2025-06-01"
    date_to: str = ""
    subreddit_allowlist: list[str] | None = None
    hn_points_threshold: int = 5


def load_config(source: str | Path | dict[str, Any]) -> ResearchConfig:
    """Load research config from a JSON file path or inline dict."""
    if isinstance(source, (str, Path)):
        path = Path(source)
        data = json.loads(path.read_text())
    else:
        data = source

    # Parse source types
    sources = [SourceType(s) for s in data["sources"]]

    return ResearchConfig(
        research_task=data["research_task"],
        search_queries=data["search_queries"],
        sources=sources,
        max_threads_per_query=data.get("max_threads_per_query", 10),
        max_comments_per_thread=data.get("max_comments_per_thread", 20),
        cache_dir=data.get("cache_dir", ".research_cache"),
        output_dir=data.get("output_dir", "20-Literature"),
        date_from=data.get("date_from", "2025-06-01"),
        date_to=data.get("date_to", ""),
        subreddit_allowlist=data.get("subreddit_allowlist"),
        hn_points_threshold=data.get("hn_points_threshold", 5),
    )


# First Upwork research config
UPWORK_RESEARCH_CONFIG = {
    "research_task": "Investigate negative opinions about Upwork on Reddit and identify effective freelance work methods.",
    "sources": ["reddit"],
    "search_queries": [
        "upwork frustrated",
        "upwork disappointed",
        "upwork negative",
        "upwork scam",
        "upwork sucks",
        "upwork impossible",
        "upwork banned",
        "upwork suspended",
        "upwork connect fees",
        "upwork declining",
        "upwork no jobs",
        "upwork client problems",
        "upwork freelancer problems",
    ],
    "max_threads_per_query": 10,
    "max_comments_per_thread": 20,
    "date_from": "2025-06-01",
    "date_to": "",
}
