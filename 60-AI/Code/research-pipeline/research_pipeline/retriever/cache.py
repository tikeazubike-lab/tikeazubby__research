"""Simple file-based HTTP response cache.

Caches API responses to disk to avoid redundant network requests.
Cache files stored as JSON under config.cache_dir.
"""
from __future__ import annotations
import json
import hashlib
from pathlib import Path
from typing import Any


class ResponseCache:
    """File-based cache for HTTP responses.

    Each cached URL is stored as a JSON file keyed by its MD5 hash.
    """

    def __init__(self, cache_dir: str = ".research_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key(self, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()

    def _path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get(self, url: str) -> dict[str, Any] | None:
        """Return cached data for URL, or None if not cached."""
        path = self._path(self._key(url))
        if path.exists():
            try:
                return json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                return None
        return None

    def set(self, url: str, data: dict[str, Any]) -> None:
        """Cache data for URL."""
        path = self._path(self._key(url))
        path.write_text(json.dumps(data, indent=2, default=str))
