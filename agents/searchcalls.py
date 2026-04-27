"""Market trend intelligence — GPT thinking + SERP API + Gemini trend tagging.

Generates strategic search queries from scraped Instagram data,
executes them via SERP API (in parallel), and packages trend signals.

All prompts are NICHE-AGNOSTIC: the LLM infers the domain and audience
from the Apify data and tailors queries accordingly.
"""
from __future__ import annotations

import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

from tools.cache import SERP_TTL, cache_get, cache_set, make_cache_key
from tools.gemini_client import generate_gemini
from tools.serp import organic_search, trends_timeseries

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

gpt_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

QUERY_AGENT = "openai/gpt-oss-120b:free"
TREND_CLASSIFIER = "gemini-flash-latest"

GENERIC_TAGS = {"fyp", "explore", "trending", "viral", "reels", "instagram"}


def _gpt_text(system: str, user: str, temperature: float = 0.5) -> str:
    response = gpt_client.chat.completions.create(
        model=QUERY_AGENT,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
    )
    return (response.choices[0].message.content or "").strip()


def _parse_json_array(raw_text: str) -> list[str]:
    cleaned = re.sub(r"```json\s*|```\s*", "", raw_text).strip()
    match = re.search(r"\[", cleaned)
    if match:
        cleaned = cleaned[match.start():]
    queries = json.loads(cleaned)
    if not isinstance(queries, list):
        raise ValueError("Model response is not a JSON array of strings")
    return [str(q).strip() for q in queries if str(q).strip()]


def _get_brand_username(intelligence: dict) -> str:
    for uname, data in intelligence.items():
        if data.get("is_brand"):
            return uname
    return "your_brand"


def plan_queries_from_usernames(primary_username: str, competitor_usernames: list[str]) -> list[str]:
    """Lightweight query planner used before scraping completes.

    Uses only validated usernames, so this can run in parallel with Apify scraping.
    """
    current_date = datetime.now().strftime("%B %Y")
    system = (
        "You generate strategic Google queries for Instagram competitive research. "
        "Return ONLY a JSON array of exactly 5 strings."
    )
    user = f"""Primary brand: @{primary_username}
Competitors: {", ".join('@' + c for c in competitor_usernames) if competitor_usernames else 'none'}
Date: {current_date}

Generate 5 concise Google queries to discover:
1) rising Instagram formats and hooks in the niche
2) competitor content gaps
3) emerging hashtags/themes
4) audience pain points and intent signals
5) near-term seasonal or cultural opportunities

Return only JSON array of 5 strings.
"""
    try:
        raw_text = _gpt_text(system, user, temperature=0.5)
        parsed = _parse_json_array(raw_text)[:5]
        if len(parsed) < 3:
            raise ValueError("Planner returned too few usable queries.")
        return parsed
    except Exception as exc:
        logger.warning("Query planner fallback triggered: %s", exc)
        return [
            f"instagram content trends for @{primary_username} niche {current_date}",
            f"@{primary_username} competitor analysis instagram hooks",
            f"instagram hashtag trends similar to {' '.join(competitor_usernames[:2])}",
            f"instagram reels vs carousel performance in this niche",
            f"seasonal instagram campaign ideas {current_date}",
        ]


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
# GPT THINKING LAYER
# ─────────────────────────────────────────────

def _generate_search_queries(intelligence: dict) -> list[str]:
    """Use GPT-OSS to generate strategic, niche-aware search queries
    based entirely on the scraped Instagram data.
    
    The LLM infers the niche, audience, and market from the data.
    """
    summary = _summarize_intelligence(intelligence)
    brand_username = _get_brand_username(intelligence)
    current_date = datetime.now().strftime("%B %Y")

    system = "You are a social media strategist analyzing Instagram data. You MUST respond with ONLY a valid JSON array of exactly 5 query strings. No explanation, no markdown, no code fences — just the JSON array."

    user = f"""Here is the competitive intelligence data:
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

    logger.info("GPT-OSS thinking: generating strategic search queries...")
    raw_text = _gpt_text(system, user, temperature=0.7)
    logger.info("GPT raw response: %s", raw_text[:200])
    queries = _parse_json_array(raw_text)[:5]
    if len(queries) < 3:
        raise ValueError("GPT-OSS returned too few usable search queries")
    logger.info("GPT-OSS generated %d queries:", len(queries))
    for i, q in enumerate(queries, 1):
        logger.info("  %d. %s", i, q)

    return queries


def _classify_major_trends(
    intelligence: dict,
    queries: list[str],
    serp_results: dict[str, list],
    google_trends_data: dict,
) -> list[str]:
    """Use Gemini to map signals into major trend buckets."""
    snippets: list[str] = []
    for query in queries[:5]:
        for item in (serp_results.get(query) or [])[:3]:
            if isinstance(item, dict):
                title = str(item.get("title") or "").strip()
                snippet = str(item.get("snippet") or "").strip()
                text = " | ".join(part for part in [title, snippet] if part)
                if text:
                    snippets.append(text)

    hashtags: list[str] = []
    for data in intelligence.values():
        hashtags.extend(data.get("analytics", {}).get("all_hashtags_used", []))
    top_hashtags = hashtags[:30]

    trend_keyword = google_trends_data.get("keyword") if isinstance(google_trends_data, dict) else None

    system = (
        "You are a social trend classifier for Instagram strategy. "
        "Return ONLY valid JSON with key major_trends (array of exactly 5 concise strings)."
    )
    user = f"""Classify major trend buckets from the signals below.

Search queries: {queries}
SERP snippets: {snippets[:15]}
Top hashtags: {top_hashtags}
Google trend keyword: {trend_keyword}

Return exactly 5 trend buckets relevant for content planning.
Examples of style: IPL season, festive season, meme wave, creator collaboration wave, product launch season.

JSON shape:
{{"major_trends": ["...", "...", "...", "...", "..."]}}"""

    try:
        raw_text, key_slot = generate_gemini(
            model=TREND_CLASSIFIER,
            system_prompt=system,
            user_prompt=user,
            temperature=0.4,
            max_output_tokens=1024,
            json_mode=True,
        )
        logger.debug("Gemini trend classifier used key slot #%d", key_slot)
        cleaned = re.sub(r"```json\s*|```\s*", "", raw_text).strip()
        payload = json.loads(cleaned)
        values = payload.get("major_trends", []) if isinstance(payload, dict) else []
        trends = [str(v).strip() for v in values if str(v).strip()][:5]
        if len(trends) >= 3:
            return trends
    except Exception as exc:
        logger.warning("Major trend classification fallback triggered: %s", exc)

    fallback: list[str] = []
    if trend_keyword:
        fallback.append(str(trend_keyword))
    fallback.extend([
        "Festive season moments",
        "Meme and pop-culture hooks",
        "Creator collaboration wave",
        "Campaign or launch season",
    ])
    seen: set[str] = set()
    deduped: list[str] = []
    for item in fallback:
        key = item.lower().strip()
        if key in seen or not key:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:5]


# ─────────────────────────────────────────────
# PARALLEL SERP EXECUTION
# ─────────────────────────────────────────────

def _execute_serp_queries(queries: list[str], num_results: int = 5) -> dict:
    """Execute SERP searches in parallel using ThreadPoolExecutor."""
    logger.info(f"Executing {len(queries)} SERP searches in parallel...")
    serp_results: dict[str, list] = {}
    misses: list[str] = []

    for query in queries:
        q_key = make_cache_key("serp_query_result", query.strip().lower(), num_results)
        cached = cache_get(q_key)
        if cached is not None:
            serp_results[query] = cached
        else:
            misses.append(query)

    if not misses:
        return serp_results

    with ThreadPoolExecutor(max_workers=min(len(misses), 5)) as executor:
        future_to_query = {
            executor.submit(organic_search, query, num_results): query
            for query in misses
        }
        for future in as_completed(future_to_query):
            query = future_to_query[future]
            try:
                result = future.result()
                serp_results[query] = result
                q_key = make_cache_key("serp_query_result", query.strip().lower(), num_results)
                cache_set(q_key, result, SERP_TTL)
                logger.info(f"  ✓ {query[:60]}...")
            except Exception as exc:
                logger.warning(f"  ✗ SERP failed for '{query[:60]}': {exc}")
                serp_results[query] = []

    return serp_results


def _derive_top_hashtag(intelligence: dict) -> str | None:
    all_hashtags: list[str] = []
    for data in intelligence.values():
        all_hashtags.extend(data.get("analytics", {}).get("all_hashtags_used", []))

    hashtag_freq: dict[str, int] = {}
    for tag in all_hashtags:
        hashtag_freq[tag] = hashtag_freq.get(tag, 0) + 1

    sorted_tags = sorted(hashtag_freq, key=hashtag_freq.get, reverse=True)
    return next((t for t in sorted_tags if t.lower() not in GENERIC_TAGS), None)


def _get_market_trends_impl(intelligence: dict, queries: list[str]) -> dict:
    top_hashtag = _derive_top_hashtag(intelligence)

    serp_results: dict[str, list] = {}
    google_trends_data: dict = {}

    with ThreadPoolExecutor(max_workers=2) as executor:
        serp_future = executor.submit(_execute_serp_queries, queries)
        trends_future = None
        if top_hashtag:
            trends_future = executor.submit(trends_timeseries, top_hashtag)

        serp_results = serp_future.result()
        if trends_future is not None:
            try:
                google_trends_data = {
                    "keyword": top_hashtag,
                    "data": trends_future.result(),
                }
            except Exception as exc:
                logger.warning(f"Google Trends failed for #{top_hashtag}: {exc}")

    major_trends = _classify_major_trends(
        intelligence=intelligence,
        queries=queries,
        serp_results=serp_results,
        google_trends_data=google_trends_data,
    )

    return {
        "search_queries": queries,
        "serp_results": serp_results,
        "google_trends_timeseries": google_trends_data,
        "major_trends": major_trends,
        "_meta": {
            "total_searches": len(queries),
            "top_hashtag": top_hashtag,
            "primary_trend": major_trends[0] if major_trends else None,
            "brands_analyzed": list(intelligence.keys()),
        },
    }


# ─────────────────────────────────────────────
# MAIN TREND FETCHER
# ─────────────────────────────────────────────

def get_market_trends(intelligence: dict) -> dict:
    """Full market trend pipeline:
    1. GPT-OSS infers niche + generates search queries
    2. SERP API executes queries (in parallel)
    3. Google Trends for top meaningful hashtag
    4. Gemini classifies major trend buckets (IPL/festive/meme etc.)
    5. Package everything
    """

    queries = _generate_search_queries(intelligence)
    return _get_market_trends_impl(intelligence, queries)


def get_market_trends_with_planned_queries(intelligence: dict, planned_queries: list[str]) -> dict:
    """Same trend pipeline but reuses pre-planned queries from a parallel DAG branch."""
    queries = [q.strip() for q in planned_queries if q and q.strip()]
    if len(queries) < 3:
        queries = _generate_search_queries(intelligence)
    return _get_market_trends_impl(intelligence, queries[:5])