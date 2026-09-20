"""Rebuildable projections over the AIOS v3.0 world.

World truth lives in the versioned world store. Query modules may be rebuilt and
must expose freshness/watermark state rather than pretending a stale projection is
current.
"""

from .search import (
    MindSearchHit,
    MindSearchPage,
    SearchHit,
    SearchPage,
    WorldSearchIndex,
    derive_dimension,
    normalize_alias,
    tokens_for,
)

__all__ = [
    "MindSearchHit",
    "MindSearchPage",
    "SearchHit",
    "SearchPage",
    "WorldSearchIndex",
    "derive_dimension",
    "normalize_alias",
    "tokens_for",
]
