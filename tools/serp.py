import os
import logging
from serpapi import GoogleSearch
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SERP_API_KEY = os.getenv("SERP_API_KEY")


def organic_search(query: str, num_results: int = 5) -> list[dict]:
    """Single Google organic search via SERP API."""
    params = {
        "q":       query,
        "api_key": SERP_API_KEY,
        "num":     num_results,
        "hl":      "en",
        "gl":      "in",
    }
    results = GoogleSearch(params).get_dict()
    organic = results.get("organic_results", [])

    return [
        {
            "title":   r.get("title"),
            "snippet": r.get("snippet"),
            "link":    r.get("link"),
        }
        for r in organic[:num_results]
    ]


def trends_timeseries(keyword: str) -> list[dict]:
    """Google Trends timeseries for a keyword (India-scoped)."""
    params = {
        "engine":    "google_trends",
        "q":         keyword,
        "api_key":   SERP_API_KEY,
        "data_type": "TIMESERIES",
        "geo":       "IN",
    }
    results = GoogleSearch(params).get_dict()
    return results.get("interest_over_time", {}).get("timeline_data", [])


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