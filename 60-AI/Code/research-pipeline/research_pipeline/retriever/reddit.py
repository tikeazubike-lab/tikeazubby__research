"""Reddit retriever using web scraping of old.reddit.com.

Scrapes old.reddit.com search results and comments as a fallback when
the official Reddit API is unavailable or rate-limited.
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup

from ..config import ResearchConfig
from ..models import Comment, RawDocument, SourceType
from .base import BaseRetriever

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class RedditRetriever(BaseRetriever):
    """Scrapes old.reddit.com for search results and comments.

    Search results are parsed from old.reddit.com/search. Each result
    becomes a RawDocument. Thread comments are fetched separately via
    fetch_comments().
    """

    def __init__(self, config: ResearchConfig, cache: Any | None = None):
        super().__init__(config, cache)
        self.client = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=30.0,
        )
        self._last_request = 0.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _rate_limit(self) -> None:
        """Ensure ~1.5 s between requests to respect robots.txt."""
        elapsed = time.time() - self._last_request
        if elapsed < 1.5:
            time.sleep(1.5 - elapsed)
        self._last_request = time.time()

    def _fetch(self, url: str) -> str | None:
        """Fetch *url* with caching and rate limiting.

        Returns the HTML string on success, or *None* on failure.
        Prints a warning on failure.
        """
        if self.cache is not None:
            cached = self.cache.get(url)
            if cached is not None and "html" in cached:
                return cached["html"]

        self._rate_limit()
        try:
            resp = self.client.get(url)
            resp.raise_for_status()
            html = resp.text
        except Exception as exc:
            print(f"[WARN] Failed to fetch {url}: {exc}")
            return None

        if self.cache is not None:
            self.cache.set(url, {"html": html})

        return html

    def _is_within_date_range(self, timestamp: str) -> bool:
        """Return *True* if *timestamp* falls within the configured date range.

        Unparseable timestamps are included (returns *True*).
        Comparison is performed against ``config.date_from`` and
        ``config.date_to`` (ISO-format strings).
        """
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return True

        date_from = self.config.date_from
        date_to = self.config.date_to

        if date_from:
            try:
                from_dt = datetime.fromisoformat(date_from)
                if dt < from_dt:
                    return False
            except (ValueError, TypeError):
                pass

        if date_to:
            try:
                to_dt = datetime.fromisoformat(date_to)
                if dt > to_dt:
                    return False
            except (ValueError, TypeError):
                pass

        return True

    # ------------------------------------------------------------------
    # Public interface (implements BaseRetriever)
    # ------------------------------------------------------------------

    def retrieve(self, query: str) -> list[RawDocument]:
        """Search old.reddit.com and return matching documents.

        URL format: ``https://old.reddit.com/search?q=<query>&sort=relevance&t=all``
        Results are parsed from ``div.search-result`` or (fallback)
        ``div.thing.link`` elements.  Each result is filtered by the
        configured date range before being returned.
        """
        url = (
            f"https://old.reddit.com/search"
            f"?q={query.replace(' ', '+')}&sort=relevance&t=all"
        )
        html = self._fetch(url)
        if html is None:
            return []

        soup = BeautifulSoup(html, "html.parser")
        documents: list[RawDocument] = []

        # Old Reddit shows results as div.search-result in the search
        # results layout, or as div.thing.link in the standard listing.
        search_results = soup.select("div.search-result")
        if not search_results:
            search_results = soup.select("div.thing.link")

        for result in search_results:
            # ---- Title & URL ----
            title_el = result.select_one("a.search-title")
            if not title_el:
                title_el = result.select_one("p.title > a")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            if href.startswith("/"):
                href = "https://old.reddit.com" + href

            # ---- Source ID ----
            result_id = result.get("id", "")
            source_id = result_id.replace("thing_t3_", "")

            # ---- Score ----
            score_el = result.select_one(
                "div.score.unvoted, span.score.unvoted, span.search-score"
            )
            score = 0
            if score_el is not None:
                score_text = (
                    score_el.get_text(strip=True)
                    .replace("points", "")
                    .replace("point", "")
                    .strip()
                )
                try:
                    score = int(score_text)
                except ValueError:
                    score = 0

            # ---- Subreddit ----
            subreddit_el = result.select_one("a.subreddit")
            if not subreddit_el:
                subreddit_el = result.select_one("a[href^='/r/']")
            subreddit = subreddit_el.get_text(strip=True) if subreddit_el else None

            # ---- Author ----
            author_el = result.select_one("a.author")
            author = author_el.get_text(strip=True) if author_el else None

            # ---- Timestamp ----
            time_el = result.select_one("time")
            timestamp = time_el.get("datetime", "") if time_el else ""

            doc = RawDocument(
                source_type=SourceType.REDDIT,
                source_id=source_id,
                title=title,
                url=href,
                score=score,
                subreddit_or_section=subreddit,
                author=author,
                timestamp=timestamp,
                content="",
                metadata={"query": query},
            )

            if self._is_within_date_range(timestamp):
                documents.append(doc)

        return documents

    def fetch_comments(self, document: RawDocument) -> None:
        """Fetch the full thread page and populate *document.comments*.

        Parses the self-text (``div.expando div.usertext-body``) into
        ``document.content`` and each top-level comment
        (``div.thing[id^='thing_t1_'] > div.entry > div.usertext-body``)
        into ``Comment`` objects.  The first parsed comment is marked
        ``is_top_comment=True``.
        """
        html = self._fetch(document.url)
        if html is None:
            return

        soup = BeautifulSoup(html, "lxml")

        # ---- Self-text (post body) ----
        post = soup.select_one(f"div#thing_t3_{document.source_id}")
        if post is not None:
            self_text_el = post.select_one(
                "div.expando div.usertext-body div.md"
            ) or post.select_one("div.usertext-body div.md")
            if self_text_el is not None:
                document.content = self_text_el.get_text(strip=True)
        else:
            self_text_el = soup.select_one("div.usertext-body div.md")
            if self_text_el is not None:
                document.content = self_text_el.get_text(strip=True)

        # ---- Comments ----
        comment_divs = soup.select("div.thing[id^='thing_t1_']")
        comments: list[Comment] = []
        for i, comment_div in enumerate(comment_divs):
            entry = comment_div.select_one("div.entry")
            if entry is None:
                continue

            body_el = entry.select_one("div.usertext-body div.md")
            if body_el is None:
                continue

            body = body_el.get_text(strip=True)
            if not body:
                continue  # skip deleted / empty comments

            cid = comment_div.get("id", "").replace("thing_t1_", "")

            author_el = entry.select_one("a.author")
            author = author_el.get_text(strip=True) if author_el else ""

            score_el = entry.select_one("span.score.unvoted")
            score = 0
            if score_el is not None:
                score_text = (
                    score_el.get_text(strip=True)
                    .replace("points", "")
                    .replace("point", "")
                    .strip()
                )
                try:
                    score = int(score_text)
                except ValueError:
                    score = 0

            comment = Comment(
                id=cid,
                author=author,
                body=body,
                score=score,
                is_top_comment=(i == 0),
            )
            comments.append(comment)

        document.comments = comments
