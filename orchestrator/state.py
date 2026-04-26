"""Graph state schema for the content strategy pipeline.

Only fields that are actively populated by node functions are declared.
"""
from __future__ import annotations

from typing import Any, TypedDict


class ContentStrategyState(TypedDict, total=False):
    # ── Inputs ──────────────────────────────────────────
    primary_ig_url: str
    competitor_ig_urls: list[str]
    primary_username: str
    competitor_usernames: list[str]

    # ── Scraping outputs ────────────────────────────────
    apify_brand_intelligence: dict[str, Any]

    # ── Market trend outputs ────────────────────────────
    market_trends: dict[str, Any]
    available_trends: list[str]
    selected_trend: str

    # ── Analysis outputs ────────────────────────────────
    gap_analysis: dict[str, Any]
    regenerated_post_prompts: dict[str, Any]
    regeneration_error: str

    # ── Final output ────────────────────────────────────
    final_recommendations: dict[str, Any]

    # ── Meta / debug ────────────────────────────────────
    errors: list[str]
