"""Pipeline orchestrator — runs the full research pipeline end-to-end.

Usage:
    from research_pipeline.pipeline import run_pipeline
    docs_by_query = run_pipeline(config)
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import ResearchConfig


def run_pipeline(config: ResearchConfig) -> dict[str, list]:
    """Run the full research pipeline for a given config.

    Steps:
    1. Retrieve — search all sources with all queries (cached)
    2. Normalize — convert RawDocuments to NormalizedDocuments
    3. Deduplicate — remove exact and near-duplicate documents
    4. Rank — assess evidence confidence heuristically
    5. Compress — reduce token count for LLM consumption

    Returns: dict mapping query -> list of compressed, ranked NormalizedDocuments.
    """
    from .retriever import retrieve_all
    from .normalizer import normalize
    from .deduplicator import deduplicate
    from .ranker import rank
    from .compressor import compress_all

    print(f"[Pipeline] Starting research: {config.research_task}")
    print(f"[Pipeline] Sources: {[s.value for s in config.sources]}")
    print(f"[Pipeline] Queries: {len(config.search_queries)}")
    print(f"[Pipeline] Date range: {config.date_from} → {config.date_to or 'present'}")

    # 1. Retrieve
    print("\n--- Stage 1: Retrieve ---")
    raw_by_query = retrieve_all(config)
    total_raw = sum(len(docs) for docs in raw_by_query.values())
    print(f"[Pipeline] Retrieved {total_raw} documents total")

    # 2. Normalize
    print("\n--- Stage 2: Normalize ---")
    norm_by_query = {}
    for query, docs in raw_by_query.items():
        norm_by_query[query] = normalize(docs)
    total_norm = sum(len(docs) for docs in norm_by_query.values())
    print(f"[Pipeline] Normalized {total_norm} documents")

    # 3. Deduplicate
    print("\n--- Stage 3: Deduplicate ---")
    deduped_by_query = {}
    for query, docs in norm_by_query.items():
        deduped_by_query[query] = deduplicate(docs)
    total_deduped = sum(len(docs) for docs in deduped_by_query.values())
    print(f"[Pipeline] After dedup: {total_deduped} (removed {total_norm - total_deduped})")

    # 4. Rank
    print("\n--- Stage 4: Rank ---")
    ranked_by_query = {}
    for query, docs in deduped_by_query.items():
        ranked_by_query[query] = rank(docs)
    print(f"[Pipeline] Ranking complete")

    # 5. Compress
    print("\n--- Stage 5: Compress ---")
    compressed_by_query = {}
    for query, docs in ranked_by_query.items():
        compressed_by_query[query] = compress_all(docs)
    print(f"[Pipeline] Compression complete")

    print(f"\n[Pipeline] Done. {total_raw} retrieved → {total_deduped} unique → ready for synthesis.")
    return compressed_by_query
