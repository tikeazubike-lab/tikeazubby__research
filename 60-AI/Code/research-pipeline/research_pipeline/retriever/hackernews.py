"""Hacker News retriever using the Algolia Search API.

API docs: https://hn.algolia.com/api
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from ..config import ResearchConfig
from ..models import Comment, RawDocument, SourceType
from .base import BaseRetriever

API_BASE = "https://hn.algolia.com/api/v1"


def _iso_to_unix(iso_date: str) -> int:
    """Convert an ISO date string (e.g. ``"2025-06-01"``) to a Unix timestamp."""
    if not iso_date:
        return 0
    dt = datetime.fromisoformat(iso_date)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


class HNRetriever(BaseRetriever):
    """Retriever for Hacker News stories and comments via the Algolia Search API."""

    def __init__(self, config: ResearchConfig, cache: Any | None = None):
        super().__init__(config, cache)
        self.client = httpx.Client(timeout=30.0)

    # ------------------------------------------------------------------
    # retrieve
    # ------------------------------------------------------------------
    def retrieve(self, query: str) -> list[RawDocument]:
        """Search Hacker News stories matching *query*.

        Returns a list of :class:`RawDocument` objects (without comments
        populated — call :meth:`fetch_comments` to fill those in).
        """
        # -- build numericFilters -------------------------------------------
        numeric_filters: list[str] = []

        # date_from (mandatory: config defaults to "2025-06-01")
        ts_from = _iso_to_unix(self.config.date_from)
        if ts_from:
            numeric_filters.append(f"created_at_i>={ts_from}")

        # date_to (optional)
        if self.config.date_to:
            ts_to = _iso_to_unix(self.config.date_to)
            if ts_to:
                numeric_filters.append(f"created_at_i<={ts_to}")

        # points threshold
        threshold = self.config.hn_points_threshold
        if threshold > 0:
            numeric_filters.insert(0, f"points>={threshold}")

        # -- build URL ------------------------------------------------------
        params = (
            f"query={query}"
            f"&tags=story"
            f"&hitsPerPage={self.config.max_threads_per_query}"
        )
        if numeric_filters:
            params += "&numericFilters=" + ",".join(numeric_filters)

        url = f"{API_BASE}/search?{params}"

        # -- fetch (or cache-hit) -------------------------------------------
        cached = self.cache.get(url) if self.cache else None
        if cached is not None:
            data = cached
        else:
            resp = self.client.get(url)
            resp.raise_for_status()
            data = resp.json()
            if self.cache:
                self.cache.set(url, data)

        # -- parse hits -----------------------------------------------------
        documents: list[RawDocument] = []
        for hit in data.get("hits", []):
            object_id = str(hit.get("objectID") or "")
            if not object_id:
                continue

            title = hit.get("title") or ""
            story_url = hit.get("url") or (
                f"https://news.ycombinator.com/item?id={object_id}"
            )
            points = hit.get("points") or 0
            author = hit.get("author") or ""
            created_at_i = hit.get("created_at_i")
            timestamp = (
                datetime.fromtimestamp(created_at_i, tz=timezone.utc).isoformat()
                if created_at_i
                else ""
            )
            story_text = hit.get("story_text") or ""
            num_comments = hit.get("num_comments") or 0

            doc = RawDocument(
                source_type=SourceType.HACKER_NEWS,
                source_id=object_id,
                title=title,
                url=story_url,
                score=points,
                author=author,
                timestamp=timestamp,
                content=story_text,
                metadata={"num_comments": num_comments},
            )
            documents.append(doc)

        return documents

    # ------------------------------------------------------------------
    # fetch_comments
    # ------------------------------------------------------------------
    def fetch_comments(self, document: RawDocument) -> None:
        """Populate *document.comments* with top-level comments."""
        url = f"{API_BASE}/items/{document.source_id}"

        # -- fetch (or cache-hit) -------------------------------------------
        cached = self.cache.get(url) if self.cache else None
        if cached is not None:
            data = cached
        else:
            resp = self.client.get(url)
            resp.raise_for_status()
            data = resp.json()
            if self.cache:
                self.cache.set(url, data)

        # -- parse children -------------------------------------------------
        comments: list[Comment] = []
        max_comments = self.config.max_comments_per_thread
        for child in data.get("children", []):
            if child.get("deleted") or child.get("removed"):
                continue
            text = (child.get("text") or "").strip()
            if not text:
                continue

            comments.append(
                Comment(
                    id=str(child["id"]),
                    author=child.get("author") or "",
                    body=text,
                    score=child.get("points") or 0,
                )
            )
            if len(comments) >= max_comments:
                break

        document.comments = comments
