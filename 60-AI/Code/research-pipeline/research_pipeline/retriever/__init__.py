"""Retriever registry — maps SourceType to Retriever class.

Factory function create_retriever() returns the appropriate retriever for a source type.
Utility function retrieve_all() runs all configured retrievers for all queries.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from .cache import ResponseCache
from .base import BaseRetriever

if TYPE_CHECKING:
    from ..models import SourceType, ResearchConfig, RawDocument


# Lazy imports to avoid circular deps
_RETRIEVERS: dict[str, type[BaseRetriever]] = {}


def _ensure_registered():
    if not _RETRIEVERS:
        from ..models import SourceType
        from .reddit import RedditRetriever
        from .hackernews import HNRetriever
        from .github import GithubRetriever

        _RETRIEVERS[SourceType.REDDIT.value] = RedditRetriever
        _RETRIEVERS[SourceType.HACKER_NEWS.value] = HNRetriever
        _RETRIEVERS[SourceType.GITHUB.value] = GithubRetriever


def create_retriever(source_type: SourceType, config: ResearchConfig, cache: ResponseCache | None = None) -> BaseRetriever:
    """Factory: create the appropriate retriever for a source type."""
    _ensure_registered()
    cls = _RETRIEVERS.get(source_type.value)
    if not cls:
        raise ValueError(f"Unsupported source type: {source_type}")
    return cls(config, cache=cache)


def retrieve_all(config: ResearchConfig) -> dict[str, list[RawDocument]]:
    """Run all configured retrievers for all queries. Returns {query: [documents]}."""
    from ..models import SourceType

    cache = ResponseCache(config.cache_dir)
    results: dict[str, list[RawDocument]] = {}

    for query in config.search_queries:
        query_results: list[RawDocument] = []
        for source_type in config.sources:
            retriever = create_retriever(source_type, config, cache)
            docs = retriever.retrieve(query)
            # Fetch comments for each document
            for doc in docs:
                retriever.fetch_comments(doc)
            query_results.extend(docs)
            print(f"  [INFO] {source_type.value} | '{query}' | {len(docs)} docs")
        results[query] = query_results

    return results
