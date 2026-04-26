import os
import logging
from serpapi import GoogleSearch
from dotenv import load_dotenv

from tools.cache import SERP_TTL, TRENDS_TTL, cache_get, cache_set, make_cache_key

load_dotenv()

logger = logging.getLogger(__name__)

SERP_API_KEY = os.getenv("SERP_API_KEY")


def organic_search(query: str, num_results: int = 5) -> list[dict]:
    """Single Google organic search via SERP API."""
    cache_key = make_cache_key("serp_organic", query.strip().lower(), num_results, "en", "in")
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    params = {
        "q":       query,
        "api_key": SERP_API_KEY,
        "num":     num_results,
        "hl":      "en",
        "gl":      "in",
    }
    results = GoogleSearch(params).get_dict()
    organic = results.get("organic_results", [])

    parsed = [
        {
            "title":   r.get("title"),
            "snippet": r.get("snippet"),
            "link":    r.get("link"),
        }
        for r in organic[:num_results]
    ]
    cache_set(cache_key, parsed, SERP_TTL)
    return parsed


def trends_timeseries(keyword: str) -> list[dict]:
    """Google Trends timeseries for a keyword (India-scoped)."""
    timeframe = "default"
    cache_key = make_cache_key("google_trends_timeseries", [keyword.strip().lower()], timeframe, "IN")
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    params = {
        "engine":    "google_trends",
        "q":         keyword,
        "api_key":   SERP_API_KEY,
        "data_type": "TIMESERIES",
        "geo":       "IN",
    }
    results = GoogleSearch(params).get_dict()
    parsed = results.get("interest_over_time", {}).get("timeline_data", [])
    cache_set(cache_key, parsed, TRENDS_TTL)
    return parsed


def related_queries(keyword: str) -> dict:
    """Returns rising and top related queries for a keyword."""
    params = {
        "engine":    "google_trends",
        "q":         keyword,
        "api_key":   SERP_API_KEY,
        "data_type": "RELATED_QUERIES",
        "geo":       "IN",
    }
    results = GoogleSearch(params).get_dict()
    
    return results.get("related_queries", {})