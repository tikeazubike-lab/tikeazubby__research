"""GitHub retriever using the public Search API.

Uses https://api.github.com/search/ endpoint.
Rate-limited to ~60 req/hr when unauthenticated.
"""
from __future__ import annotations

import time
import warnings
from typing import Any

import httpx

from ..config import ResearchConfig
from ..models import Comment, RawDocument, SourceType
from .base import BaseRetriever
from .cache import ResponseCache


class GithubRetriever(BaseRetriever):
    """Retrieve GitHub repositories and issues via the public Search API.

    Respects rate limits with a 2-second delay between requests.
    Caches responses to disk via ResponseCache.
    """

    API_BASE = "https://api.github.com"

    def __init__(
        self,
        config: ResearchConfig,
        cache: ResponseCache | None = None,
        token: str | None = None,
    ):
        """Initialise the GitHub retriever.

        Args:
            config: ResearchConfig with date_from/date_to filtering.
            cache: Optional ResponseCache instance. Creates one if omitted.
            token: Optional GitHub personal access token for higher rate limits.
        """
        super().__init__(config, cache)
        self.token = token
        headers = {
            "User-Agent": "ResearchPipeline/1.0",
            "Accept": "application/vnd.github.v3+json",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.Client(headers=headers, timeout=30.0)
        if self.cache is None:
            self.cache = ResponseCache(config.cache_dir)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _rate_limit(self) -> None:
        """Wait 2 seconds to avoid hitting GitHub's unauthenticated rate limit

        (60 requests per hour ≈ 1 request per 60 s; a 2 s pause is generous
        enough for unauthenticated use and keeps us well under the cap).
        """
        time.sleep(2)

    def _search(self, endpoint: str, query: str) -> list[dict]:
        """Generic search helper for the GitHub Search API.

        Rate-limits first, then builds the URL, consults the disk cache,
        and on miss issues a GET request.  Failed / errored requests
        return an empty list with a warning.

        Args:
            endpoint: API path segment (e.g. ``"repositories"``, ``"issues"``).
            query: Raw search query string (without date qualifier).

        Returns:
            List of result items from the ``items`` key of the API response.
        """
        self._rate_limit()

        # Append date qualifier when the config specifies a lower bound
        full_query = query
        if self.config.date_from:
            full_query = f"{query}+created:>={self.config.date_from}"

        max_per_page = min(self.config.max_threads_per_query, 100)
        url = (
            f"{self.API_BASE}/search/{endpoint}"
            f"?q={full_query}"
            f"&sort=stars&order=desc&per_page={max_per_page}"
        )

        # --- cache check ---
        cached = self.cache.get(url)
        if cached is not None:
            return cached.get("items", [])

        # --- live request ---
        try:
            resp = self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            warnings.warn(
                f"GitHub API HTTP error [{exc.response.status_code}] "
                f"for {endpoint} query {query!r}: {exc}"
            )
            return []
        except httpx.RequestError as exc:
            warnings.warn(
                f"GitHub request failed for {endpoint} query {query!r}: {exc}"
            )
            return []

        self.cache.set(url, data)
        return data.get("items", [])

    # ------------------------------------------------------------------
    # Public interface (BaseRetriever contract)
    # ------------------------------------------------------------------

    def retrieve(self, query: str) -> list[RawDocument]:
        """Search GitHub repositories and issues for *query*.

        Returns a list of
        :class:`~research_pipeline.models.RawDocument` objects
        covering both repository matches and open-issue matches.
        """
        documents: list[RawDocument] = []

        # --- repositories ---
        for item in self._search("repositories", query):
            owner = item.get("owner") or {}
            documents.append(
                RawDocument(
                    source_type=SourceType.GITHUB,
                    source_id=item.get("full_name", str(item.get("id", ""))),
                    title=item.get("full_name", ""),
                    url=item.get("html_url", ""),
                    score=item.get("stargazers_count", 0),
                    subreddit_or_section=owner.get("login"),
                    author=owner.get("login"),
                    timestamp=item.get("created_at"),
                    content=item.get("description") or "",
                    metadata={
                        "type": "repository",
                        "language": item.get("language"),
                        "forks": item.get("forks_count", 0),
                        "topics": item.get("topics", []),
                        "search_query": query,
                    },
                )
            )

        # --- open issues ---
        for item in self._search("issues", f"{query}+state:open"):
            user = item.get("user") or {}
            # Derive a short repo name from the repository_url, e.g.
            # "https://api.github.com/repos/owner/name" → "owner/name"
            repo_short = ""
            repo_url: str | None = item.get("repository_url")
            if repo_url:
                repo_short = repo_url.rstrip("/").rsplit("/", 2)[-2] + "/" + repo_url.rstrip("/").rsplit("/", 1)[-1]

            documents.append(
                RawDocument(
                    source_type=SourceType.GITHUB,
                    source_id=str(item.get("id", "")),
                    title=item.get("title", ""),
                    url=item.get("html_url", ""),
                    score=item.get("score", 0),
                    subreddit_or_section=repo_short,
                    author=user.get("login"),
                    timestamp=item.get("created_at"),
                    content=item.get("body") or "",
                    metadata={
                        "type": "issue",
                        "state": item.get("state"),
                        "comments_count": item.get("comments", 0),
                        "search_query": query,
                    },
                )
            )

        return documents

    def fetch_comments(self, document: RawDocument) -> None:
        """Fetch issue comments for *document* (mutates in-place).

        Only applicable when ``document.metadata["type"] == "issue"``.
        Converts the HTML issue URL to the GitHub API comments endpoint,
        rate-limits, caches, and populates ``document.comments``.
        """
        if document.metadata.get("type") != "issue":
            return

        issue_url = document.url
        if not issue_url or "/issues/" not in issue_url:
            return

        # Convert HTML issue URL → API comments URL
        # "https://github.com/owner/repo/issues/123"
        #   → "https://api.github.com/repos/owner/repo/issues/123/comments"
        parts = issue_url.split("/issues/")
        repo_path = parts[0].replace("https://github.com/", "")
        issue_number = parts[1].split("/")[0]
        comments_url = (
            f"{self.API_BASE}/repos/{repo_path}/issues/{issue_number}/comments"
        )

        self._rate_limit()

        # --- cache check ---
        cached = self.cache.get(comments_url)
        if cached is not None:
            # The API returns a plain JSON array, so we normalise it.
            comment_items = cached if isinstance(cached, list) else cached.get("items", [])
        else:
            try:
                resp = self._client.get(comments_url)
                resp.raise_for_status()
                comment_items = resp.json()
            except httpx.HTTPStatusError as exc:
                warnings.warn(
                    f"GitHub API error fetching comments for {issue_url}: "
                    f"[{exc.response.status_code}] {exc}"
                )
                return
            except httpx.RequestError as exc:
                warnings.warn(
                    f"Request failed fetching comments for {issue_url}: {exc}"
                )
                return

            self.cache.set(comments_url, {"items": comment_items})

        # --- parse Comment objects ---
        for cm in comment_items:
            reactor = cm.get("reactions") or {}
            document.comments.append(
                Comment(
                    id=str(cm.get("id", "")),
                    author=cm.get("user", {}).get("login", "") if cm.get("user") else "",
                    body=cm.get("body", ""),
                    score=reactor.get("+1", 0),
                    is_top_comment=False,
                )
            )

        # Mark the first (chronologically earliest) comment as top comment
        if document.comments:
            document.comments[0].is_top_comment = True
