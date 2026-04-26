"""Agents package — LangGraph node functions.

Each node function takes ContentStrategyState and returns a partial
state dict. These are the functions imported by orchestrator/graph.py.

Pipeline:
    validate_input → [scrape_instagram_data + plan_queries] → join_for_trends → fetch_market_trends →
  run_analysis → generate_recommendations → END
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def _extract_available_trends(trends: dict[str, Any]) -> list[str]:
    """Build a compact trend list for UI controls."""
    discovered: list[str] = []

    for query in trends.get("search_queries", [])[:8]:
        cleaned = query.strip()
        if cleaned:
            discovered.append(cleaned)

    top_hashtag = trends.get("_meta", {}).get("top_hashtag")
    if top_hashtag:
        discovered.insert(0, f"#{top_hashtag}")

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for item in discovered:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


# ─────────────────────────────────────────────
# NODE 1: VALIDATE INPUT
# ─────────────────────────────────────────────

def validate_input_node(state: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize user inputs.
    
    Extracts Instagram usernames from URLs and ensures we have
    valid data to proceed with scraping.
    """
    errors: list[str] = []
    
    primary_url = state.get("primary_ig_url", "")
    competitor_urls = state.get("competitor_ig_urls", [])

    if not primary_url:
        errors.append("primary_ig_url is required.")
    if not competitor_urls:
        errors.append("At least one competitor_ig_url is required.")

    def _extract_username(url: str) -> str | None:
        """Extract Instagram username from URL or plain username."""
        url = url.strip().rstrip("/")
        # Handle full URLs like https://instagram.com/username
        match = re.search(r"instagram\.com/([A-Za-z0-9._]+)", url)
        if match:
            return match.group(1)
        # Handle plain usernames (with or without @)
        clean = url.lstrip("@")
        if re.match(r"^[A-Za-z0-9._]+$", clean):
            return clean
        return None

    primary_username = _extract_username(primary_url) if primary_url else None
    if primary_url and not primary_username:
        errors.append(f"Could not extract username from: {primary_url}")

    competitor_usernames = []
    for url in competitor_urls:
        uname = _extract_username(url)
        if uname:
            competitor_usernames.append(uname)
        else:
            errors.append(f"Could not extract username from: {url}")

    if errors:
        logger.error(f"Validation failed: {errors}")
        return {"errors": errors}

    logger.info(f"✓ Brand: @{primary_username}")
    logger.info(f"✓ Competitors: {['@' + u for u in competitor_usernames]}")

    return {
        "primary_username": primary_username,
        "competitor_usernames": competitor_usernames,
        "errors": [],
    }


# ─────────────────────────────────────────────
# NODE 2: SCRAPE INSTAGRAM DATA
# ─────────────────────────────────────────────

def scrape_instagram_data_node(state: dict[str, Any]) -> dict[str, Any]:
    """Scrape Instagram profiles and posts via Apify.
    
    Calls the Apify tool and structures the result as brand intelligence.
    """
    from tools.apify import get_brand_intelligence

    brand = state["primary_username"]
    competitors = state["competitor_usernames"]

    logger.info(f"Scraping Instagram data for @{brand} + {len(competitors)} competitors...")

    try:
        intelligence = get_brand_intelligence(brand, competitors)
        logger.info(f"✓ Scraped {len(intelligence)} accounts successfully.")
        return {
            "apify_brand_intelligence": intelligence,
        }
    except Exception as exc:
        msg = f"Apify scraping failed: {exc}"
        logger.error(msg)
        return {"errors": state.get("errors", []) + [msg]}


def plan_queries_node(state: dict[str, Any]) -> dict[str, Any]:
    """Plan strategic search queries from validated usernames.

    This node can run in parallel with scraping to shorten wall-clock time.
    """
    from agents.searchcalls import plan_queries_from_usernames

    try:
        queries = plan_queries_from_usernames(
            state["primary_username"],
            state.get("competitor_usernames", []),
        )
        logger.info("✓ Planned %d search queries.", len(queries))
        return {"planned_search_queries": queries}
    except Exception as exc:
        msg = f"Query planning failed: {exc}"
        logger.error(msg)
        return {"errors": state.get("errors", []) + [msg]}


def join_for_trends_node(state: dict[str, Any]) -> dict[str, Any]:
    """No-op join node used to wait for scrape + plan branches."""
    return {}


# ─────────────────────────────────────────────
# NODE 3: FETCH MARKET TRENDS (merged search + trends)
# ─────────────────────────────────────────────

def fetch_market_trends_node(state: dict[str, Any]) -> dict[str, Any]:
    """Generate search queries (Claude Haiku) → execute SERP (parallel) → Google Trends.
    
    This is the merged search intelligence + market trends node.
    Claude Haiku infers the niche from the Apify data to generate
    targeted search queries.
    """
    from agents.searchcalls import get_market_trends, get_market_trends_with_planned_queries

    intelligence = state["apify_brand_intelligence"]

    logger.info("Fetching market trends (Claude Haiku → SERP → Google Trends)...")

    try:
        planned = state.get("planned_search_queries", [])
        if planned:
            trends = get_market_trends_with_planned_queries(intelligence, planned)
        else:
            trends = get_market_trends(intelligence)
        logger.info(
            f"✓ Market trends fetched: {trends['_meta']['total_searches']} searches, "
            f"top hashtag: #{trends['_meta']['top_hashtag']}"
        )
        return {
            "market_trends": trends,
        }
    except Exception as exc:
        msg = f"Market trends failed: {exc}"
        logger.error(msg)
        return {"errors": state.get("errors", []) + [msg]}


# ─────────────────────────────────────────────
# NODE 4: RUN ANALYSIS (LLM Council)
# ─────────────────────────────────────────────

def run_analysis_node(state: dict[str, Any]) -> dict[str, Any]:
    """Run the 3-layer LLM analysis pipeline:
    Layer 1 → Gap Analysis        (Council: GPT-OSS-12B + Claude Sonnet → Claude Opus chairman)
    Layer 2 → Post Prompts        (Council)
    Layer 3 → Strategy Report     (GPT-OSS-12B)
    """
    from agents.analyzer import run_analysis

    intelligence = state["apify_brand_intelligence"]
    trends = state["market_trends"]

    logger.info("Running LLM Council analysis pipeline...")

    try:
        results = run_analysis(intelligence, trends)
        available_trends = _extract_available_trends(trends)
        logger.info("✓ Analysis pipeline complete.")
        return {
            "gap_analysis": results["gap_analysis"],
            "final_recommendations": results,
            "available_trends": available_trends,
            "selected_trend": available_trends[0] if available_trends else "",
        }
    except Exception as exc:
        msg = f"Analysis pipeline failed: {exc}"
        logger.error(msg)
        return {"errors": state.get("errors", []) + [msg]}


# ─────────────────────────────────────────────
# NODE 5: GENERATE RECOMMENDATIONS (final packaging)
# ─────────────────────────────────────────────

def generate_recommendations_node(state: dict[str, Any]) -> dict[str, Any]:
    """Package the final output for presentation.
    
    Merges gap analysis, post prompts, and strategy report
    into a structured final_recommendations payload.
    """
    logger.info("Packaging final recommendations...")

    recommendations = state.get("final_recommendations", {})

    # Add metadata
    recommendations["_meta"] = {
        "brand": f"@{state.get('primary_username', 'unknown')}",
        "competitors": [f"@{u}" for u in state.get("competitor_usernames", [])],
        "market_signals_used": state.get("market_trends", {}).get("_meta", {}),
        "active_trend": state.get("selected_trend", ""),
    }

    logger.info("✓ Final recommendations packaged.")
    return {
        "final_recommendations": recommendations,
    }


def regenerate_post_prompts_node(state: dict[str, Any]) -> dict[str, Any]:
    """Regenerate only post prompts from existing intelligence and trends."""
    from agents.analyzer import regenerate_post_prompts

    selected_trend = (state.get("selected_trend") or "").strip()
    if not selected_trend:
        return {"regeneration_error": "Please select or enter a trend first."}

    try:
        prompts = regenerate_post_prompts(
            state["apify_brand_intelligence"],
            state["market_trends"],
            selected_trend,
        )
        recommendations = dict(state.get("final_recommendations", {}))
        recommendations["post_prompts"] = prompts
        recommendations.setdefault("_meta", {})
        recommendations["_meta"]["active_trend"] = selected_trend
        return {
            "regenerated_post_prompts": prompts,
            "final_recommendations": recommendations,
            "regeneration_error": "",
        }
    except Exception as exc:
        msg = f"Post regeneration failed: {exc}"
        logger.error(msg)
        return {"regeneration_error": msg}
