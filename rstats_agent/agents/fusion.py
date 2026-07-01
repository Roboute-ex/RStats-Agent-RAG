"""Context fusion for deterministic prompt/context assembly."""

from __future__ import annotations

from collections.abc import Iterable

from rstats_agent.schemas import RetrievalResult


PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2}
SOURCE_RANK = {"official_reference": 0, "vignette": 1, "example": 2}


def fuse_context(
    results: list[RetrievalResult],
    max_chunks: int = 6,
    preferred_packages: Iterable[str] | None = None,
) -> list[RetrievalResult]:
    """Order chunks by task package first, then source priority and score."""

    preferred = {package.lower() for package in preferred_packages or []}
    pool = results
    if preferred:
        preferred_results = [item for item in results if item.package.lower() in preferred]
        if preferred_results:
            pool = preferred_results

    def package_rank(item: RetrievalResult) -> int:
        if not preferred:
            return 0
        return 0 if item.package.lower() in preferred else 1

    return sorted(
        pool,
        key=lambda item: (
            package_rank(item),
            PRIORITY_RANK.get(item.priority, 9),
            SOURCE_RANK.get(item.source_type, 9),
            -item.score,
            item.chunk_id,
        ),
    )[:max_chunks]
