from __future__ import annotations

from functools import lru_cache

from orchestrator.graph import build_graph


@lru_cache(maxsize=1)
def get_pipeline_graph():
    """Build and cache a single compiled LangGraph instance for API requests."""
    return build_graph()
