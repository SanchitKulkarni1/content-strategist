"""Market trend intelligence — Gemini thinking + SERP API + Google Trends.

Generates strategic search queries from scraped Instagram data,
executes them via SERP API (in parallel), and packages trend signals.

All prompts are NICHE-AGNOSTIC: the LLM infers the domain and audience
from the Apify data and tailors queries accordingly.
"""
from __future__ import annotations

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from dotenv import load_dotenv
from google import genai
from google.genai import types

from tools.serp import organic_search, trends_timeseries

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

GENERIC_TAGS = {"fyp", "explore", "trending", "viral", "reels", "instagram"}


def _get_brand_username(intelligence: dict) -> str:
    for uname, data in intelligence.items():
        if data.get("is_brand"):
            return uname
    return "your_brand"


# ─────────────────────────────────────────────
# INTELLIGENCE SUMMARIZER
# ─────────────────────────────────────────────

def _summarize_intelligence(intelligence: dict) -> str:
    summary = []
    for uname, data in intelligence.items():
        role      = "YOUR BRAND" if data.get("is_brand") else "COMPETITOR"
        profile   = data.get("profile", {})
        analytics = data.get("analytics", {})
        posts     = data.get("posts", [])

        top_captions = [
            p["caption"][:120] for p in posts if p.get("caption")
        ][:3]
        pinned = next((p for p in posts if p.get("is_pinned")), None)

        summary.append(f"""
--- [{role}] @{uname} ---
Followers    : {profile.get('followers', 'N/A')}
Bio          : {profile.get('bio', 'N/A')}
Avg Likes    : {analytics.get('avg_likes', 0)}
Avg Comments : {analytics.get('avg_comments', 0)}
Content Mix  : {analytics.get('content_type_mix', {})}
Top Hashtags : {analytics.get('all_hashtags_used', [])[:10]}
Collabs      : {analytics.get('influencer_collabs', [])}
Sample Captions:
{chr(10).join(f'  - {c}' for c in top_captions)}
Pinned Post  : {pinned.get('caption', 'N/A')[:120] if pinned else 'None'}
""")
    return "\n".join(summary)


# ─────────────────────────────────────────────
# GEMINI THINKING LAYER
# ─────────────────────────────────────────────

def _generate_search_queries(intelligence: dict) -> list[str]:
    """Use Gemini to generate strategic, niche-aware search queries
    based entirely on the scraped Instagram data.
    
    The LLM infers the niche, audience, and market from the data.
    """
    summary = _summarize_intelligence(intelligence)
    brand_username = _get_brand_username(intelligence)
    current_date = datetime.now().strftime("%B %Y")

    prompt = f"""You are a social media strategist analyzing Instagram data.

Here is the competitive intelligence data:
{summary}

Your task:
1. First, INFER the brand's niche, industry, and target audience from the data
   (look at bios, hashtags, captions, content types, follower counts)
2. Then generate exactly 5 precise Google search queries to uncover:
   a. Content styles/aesthetics trending in THIS specific niche on Instagram right now
   b. Gaps @{brand_username} can exploit that competitors are missing
   c. Rising hashtags or visual trends in this industry
   d. What type of posts (Reels vs images, collabs vs solo) are getting traction in this niche
   e. Seasonal or cultural trends relevant to this niche in {current_date}

Rules:
- Be SPECIFIC to the niche you inferred — not generic social media advice
- Focus on ACTIONABLE insights for Instagram content creation
- Each query should target a different angle
- Return ONLY a valid JSON array of 5 query strings, nothing else
"""

    logger.info("Gemini thinking: generating strategic search queries...")
    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7,
            response_mime_type="application/json",
        ),
    )

    raw_text = (response.text or "").strip()
    queries = json.loads(raw_text)
    if not isinstance(queries, list):
        raise ValueError("Gemini response is not a JSON array of queries")
    queries = [str(q).strip() for q in queries if str(q).strip()][:5]
    if len(queries) < 3:
        raise ValueError("Gemini returned too few usable search queries")
    logger.info(f"Gemini generated {len(queries)} queries:")
    for i, q in enumerate(queries, 1):
        logger.info(f"  {i}. {q}")

    return queries


# ─────────────────────────────────────────────
# PARALLEL SERP EXECUTION
# ─────────────────────────────────────────────

def _execute_serp_queries(queries: list[str], num_results: int = 5) -> dict:
    """Execute SERP searches in parallel using ThreadPoolExecutor."""
    logger.info(f"Executing {len(queries)} SERP searches in parallel...")
    serp_results = {}

    with ThreadPoolExecutor(max_workers=min(len(queries), 5)) as executor:
        future_to_query = {
            executor.submit(organic_search, query, num_results): query
            for query in queries
        }
        for future in as_completed(future_to_query):
            query = future_to_query[future]
            try:
                serp_results[query] = future.result()
                logger.info(f"  ✓ {query[:60]}...")
            except Exception as exc:
                logger.warning(f"  ✗ SERP failed for '{query[:60]}': {exc}")
                serp_results[query] = []

    return serp_results


# ─────────────────────────────────────────────
# MAIN TREND FETCHER
# ─────────────────────────────────────────────

def get_market_trends(intelligence: dict) -> dict:
    """Full market trend pipeline:
    1. Gemini infers niche + generates search queries
    2. SERP API executes queries (in parallel)
    3. Google Trends for top meaningful hashtag
    4. Package everything
    """

    # Step 1: Gemini decides what to search
    queries = _generate_search_queries(intelligence)

    # Step 2: Execute SERP queries in parallel
    serp_results = _execute_serp_queries(queries)

    # Step 3: Google Trends for top meaningful hashtag
    all_hashtags = []
    for data in intelligence.values():
        all_hashtags.extend(data.get("analytics", {}).get("all_hashtags_used", []))

    hashtag_freq: dict[str, int] = {}
    for tag in all_hashtags:
        hashtag_freq[tag] = hashtag_freq.get(tag, 0) + 1

    sorted_tags = sorted(hashtag_freq, key=hashtag_freq.get, reverse=True)
    top_hashtag = next(
        (t for t in sorted_tags if t.lower() not in GENERIC_TAGS), None
    )

    google_trends_data = {}
    if top_hashtag:
        logger.info(f"Fetching Google Trends for: #{top_hashtag}")
        try:
            google_trends_data = {
                "keyword": top_hashtag,
                "data":    trends_timeseries(top_hashtag),
            }
        except Exception as exc:
            logger.warning(f"Google Trends failed for #{top_hashtag}: {exc}")

    # Step 4: Package everything
    trends = {
        "gemini_queries":           queries,
        "serp_results":             serp_results,
        "google_trends_timeseries": google_trends_data,
        "_meta": {
            "total_searches":  len(queries),
            "top_hashtag":     top_hashtag,
            "brands_analyzed": list(intelligence.keys()),
        },
    }

    return trends