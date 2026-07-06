"""Abstract base class for all retrievers.

Each retriever implements:
- retrieve(query) -> list[RawDocument]: search and pull results
- fetch_comments(document) -> None: populate comments for a single document
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..config import ResearchConfig

from ..models import RawDocument


class BaseRetriever(ABC):
    """Abstract retriever. Subclasses implement retrieval for one source type."""

    def __init__(self, config: ResearchConfig, cache: Any | None = None):
        self.config = config
        self.cache = cache

    @abstractmethod
    def retrieve(self, query: str) -> list[RawDocument]:
        """Search and retrieve documents for a query from this source.
        Returns a list of RawDocument objects.
        """
        ...

    @abstractmethod
    def fetch_comments(self, document: RawDocument) -> None:
        """Fetch detailed comments for a document (mutates in-place)."""
        ...
