"""Agents package — LangGraph node functions.

Each node function takes ContentStrategyState and returns a partial
state dict. These are the functions imported by orchestrator/graph.py.

Pipeline:
  validate_input → scrape_instagram_data → fetch_market_trends →
  run_analysis → generate_recommendations → END
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


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


# ─────────────────────────────────────────────
# NODE 3: FETCH MARKET TRENDS (merged search + trends)
# ─────────────────────────────────────────────

def fetch_market_trends_node(state: dict[str, Any]) -> dict[str, Any]:
    """Generate search queries (Claude Haiku) → execute SERP (parallel) → Google Trends.
    
    This is the merged search intelligence + market trends node.
    Claude Haiku infers the niche from the Apify data to generate
    targeted search queries.
    """
    from agents.searchcalls import get_market_trends

    intelligence = state["apify_brand_intelligence"]

    logger.info("Fetching market trends (Claude Haiku → SERP → Google Trends)...")

    try:
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
        logger.info("✓ Analysis pipeline complete.")
        return {
            "gap_analysis": results["gap_analysis"],
            "final_recommendations": results,
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
    }

    logger.info("✓ Final recommendations packaged.")
    return {
        "final_recommendations": recommendations,
    }
