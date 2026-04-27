"""Simplified analysis pipeline.

Model split:
- GPT-OSS: gap analysis + strategic report
- Gemini Flash: trend classification aware post prompt generation

No council synthesis stage.
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
from pydantic import BaseModel, ValidationError

from agents.schemas import GapAnalysis, MasterReport, PostPromptList, StrategyReport
from tools.cache import make_cache_key
from tools.gemini_client import generate_gemini

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


gpt_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

GPT_MODEL = "openai/gpt-oss-120b:free"
GEMINI_MODEL = "gemini-flash-latest"

_REGEN_CACHE: dict[str, dict] = {}


def _gpt(system: str, user: str, temperature: float = 0.6, json_mode: bool = True) -> str:
    """GPT-OSS call through OpenRouter."""
    kwargs: dict[str, object] = {
        "model": GPT_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = gpt_client.chat.completions.create(**kwargs)
    return (response.choices[0].message.content or "").strip()


def _gemini_json(system: str, user: str, temperature: float = 0.8, max_output_tokens: int = 8192) -> str:
    """Gemini Flash JSON call for post generation."""
    raw, key_slot = generate_gemini(
        model=GEMINI_MODEL,
        system_prompt=system,
        user_prompt=user,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        json_mode=True,
    )
    logger.debug("Gemini post generation used key slot #%d", key_slot)
    return raw.strip()


def _parse_and_validate(raw: str, schema: type[BaseModel], retries: int = 2) -> BaseModel:
    """Parse raw JSON and validate against a Pydantic schema with retry."""
    for attempt in range(retries + 1):
        try:
            cleaned = re.sub(r"```json\s*|```\s*", "", raw).strip()
            return schema.model_validate_json(cleaned)
        except (ValidationError, json.JSONDecodeError) as exc:
            if attempt < retries:
                logger.warning("Parse attempt %d failed for %s: %s", attempt + 1, schema.__name__, exc)
                match = re.search(r"[\[{]", cleaned)
                if match:
                    raw = cleaned[match.start():]
                continue
            raise


def _top_items(values: list[str], limit: int = 6) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(value.strip())
        if len(deduped) >= limit:
            break
    return deduped


def _extract_brand_and_competitors(intelligence: dict) -> tuple[str, dict, dict[str, dict]]:
    brand_uname = next((u for u, d in intelligence.items() if d.get("is_brand")), None)
    if not brand_uname:
        raise ValueError("No brand account found in intelligence data (no is_brand=True).")
    brand = intelligence[brand_uname]
    competitors = {u: d for u, d in intelligence.items() if not d.get("is_brand")}
    return brand_uname, brand, competitors


def _extract_brand_username(intelligence: dict) -> str:
    brand_username = next((u for u, d in intelligence.items() if d.get("is_brand")), None)
    if not brand_username:
        raise ValueError("No brand account found in intelligence data.")
    return brand_username


def _pick_primary_trend(trends: dict) -> str:
    major = trends.get("major_trends", [])
    if isinstance(major, list):
        for item in major:
            item_text = str(item).strip()
            if item_text:
                return item_text

    top_tag = trends.get("_meta", {}).get("top_hashtag")
    if top_tag:
        return f"#{top_tag}"

    queries = trends.get("search_queries", [])
    if isinstance(queries, list) and queries:
        return str(queries[0]).strip()
    return "Instagram seasonal + cultural relevance"


def build_gap_context(intelligence: dict, trends: dict) -> str:
    """Compact context for gap analysis plus trend signal summary."""
    brand_uname, brand, competitors = _extract_brand_and_competitors(intelligence)
    ba = brand.get("analytics", {})
    bp = brand.get("profile", {})

    lines = [
        f"Brand @{brand_uname}",
        f"followers={bp.get('followers', 'N/A')}",
        f"avg_likes={ba.get('avg_likes', 0)} avg_comments={ba.get('avg_comments', 0)}",
        f"content_mix={ba.get('content_type_mix', {})}",
        f"top_hashtags={_top_items(ba.get('all_hashtags_used', []), 6)}",
        f"major_trends={trends.get('major_trends', [])}",
    ]

    for uname, data in competitors.items():
        ca = data.get("analytics", {})
        cp = data.get("profile", {})
        likes_delta = (ca.get("avg_likes") or 0) - (ba.get("avg_likes") or 0)
        comments_delta = (ca.get("avg_comments") or 0) - (ba.get("avg_comments") or 0)
        lines.extend(
            [
                f"Comp @{uname} followers={cp.get('followers', 'N/A')}",
                f"delta_likes={likes_delta} delta_comments={comments_delta}",
                f"comp_mix={ca.get('content_type_mix', {})}",
                f"comp_top_hashtags={_top_items(ca.get('all_hashtags_used', []), 5)}",
            ]
        )

    return "\n".join(lines)


def build_post_context(intelligence: dict) -> str:
    """Compact context for trend-based post generation."""
    brand_uname, brand, competitors = _extract_brand_and_competitors(intelligence)
    bp = brand.get("profile", {})
    ba = brand.get("analytics", {})

    brand_tags = _top_items(ba.get("all_hashtags_used", []), 10)
    competitor_tags: list[str] = []
    competitor_mix: list[str] = []
    for uname, data in competitors.items():
        ca = data.get("analytics", {})
        competitor_tags.extend(ca.get("all_hashtags_used", []))
        competitor_mix.append(f"@{uname}:{ca.get('content_type_mix', {})}")

    missed_tags = [t for t in _top_items(competitor_tags, 12) if t.lower() not in {x.lower() for x in brand_tags}][:6]
    recent_captions = [p.get("caption", "")[:100] for p in brand.get("posts", []) if p.get("caption")][:4]

    return "\n".join(
        [
            f"Brand @{brand_uname}",
            f"bio={bp.get('bio', 'N/A')}",
            f"followers={bp.get('followers', 'N/A')}",
            f"brand_content_mix={ba.get('content_type_mix', {})}",
            f"brand_collabs={_top_items(ba.get('influencer_collabs', []), 6)}",
            f"brand_top_hashtags={brand_tags}",
            f"competitor_content_mix={competitor_mix}",
            f"top_missed_hashtags={missed_tags}",
            f"recent_caption_style_samples={recent_captions}",
        ]
    )


def build_strategy_context(intelligence: dict, trends: dict) -> str:
    """Compact executive context for strategic reporting."""
    brand_uname, brand, competitors = _extract_brand_and_competitors(intelligence)
    ba = brand.get("analytics", {})
    bp = brand.get("profile", {})

    comp_rows: list[str] = []
    for uname, data in competitors.items():
        ca = data.get("analytics", {})
        comp_rows.append(
            f"@{uname}: followers={data.get('profile', {}).get('followers', 'N/A')}, "
            f"avg_likes={ca.get('avg_likes', 0)}, avg_comments={ca.get('avg_comments', 0)}"
        )

    return "\n".join(
        [
            f"Date={datetime.now().strftime('%B %Y')}",
            f"Brand @{brand_uname}",
            f"followers={bp.get('followers', 'N/A')}",
            f"avg_likes={ba.get('avg_likes', 0)} avg_comments={ba.get('avg_comments', 0)}",
            f"content_mix={ba.get('content_type_mix', {})}",
            f"competitors={comp_rows}",
            f"major_trends={trends.get('major_trends', [])}",
        ]
    )


def _layer_gap_gpt(context: str, brand_username: str) -> str:
    system = """You are a senior social media strategist and competitive analyst.
Infer the brand's niche, target audience, and market positioning from the data.
Analyze strengths, weaknesses, competitive gaps, and market opportunities.
Every insight MUST reference specific data points. Return valid JSON only."""

    user = f"""Analyze competitive intelligence for @{brand_username}:

{context}

Return JSON:
- overall_score: {{brand_rating (1-10), vs_competitors}}
- strengths: [{{area, evidence, score}}]
- weaknesses: [{{area, evidence, impact}}]
- competitor_advantages: [{{competitor, advantage, how_to_counter}}]
- quick_wins: [{{action, expected_impact, effort}}]
- market_opportunities: [{{opportunity, trend_signal, urgency}}]"""

    return _gpt(system, user, temperature=0.4, json_mode=True)


def _layer_posts_gemini(context: str, brand_username: str, primary_trend: str, major_trends: list[str]) -> str:
    system = """You are a creative director specializing in Instagram growth.
Generate exactly 5 trend-aligned post briefs in valid JSON only.
No markdown. No explanations."""

    user = f"""Create 5 Instagram post prompts for @{brand_username}.

Brand context:
{context}

Active trend to prioritize: {primary_trend}
Major trend buckets (for thematic alignment): {major_trends}

Hard rules:
- Every post MUST align to the active trend and one major trend bucket
- Trend category can include examples like: IPL/Cricket season, festive season, meme wave, creator collab wave, launch season
- Keep ideas practical and shootable

Return JSON with a "posts" array. Each post:
- post_number, gap_addressed, format (Reel/Carousel/Static Image)
- hook, concept, caption (with emojis), hashtags (list)
- call_to_action, posting_time, why_this_wins"""

    return _gemini_json(system, user, temperature=0.85)


def _layer_report_gpt(context: str, brand_username: str) -> str:
    system = """You are a brand consultant writing a concise strategic brief.
Write in clear, direct language. Every sentence must be actionable.
You MUST return valid JSON with exactly these keys:
- executiveSummary (string)
- top3Fixes (array of 3 short strings)
- doubleDownOn (array of 3 short strings)
- thirtyDayPlan (array of 4 short strings)
No markdown fences, no extra keys."""

    user = f"""Create the strategic report JSON (max 400 words total) for @{brand_username}.

{context}

Return exact shape:
{{
  "executiveSummary": "...",
  "top3Fixes": ["...", "...", "..."],
  "doubleDownOn": ["...", "...", "..."],
  "thirtyDayPlan": ["Week 1 ...", "Week 2 ...", "Week 3 ...", "Week 4 ..."]
}}"""

    return _gpt(system, user, temperature=0.5, json_mode=True)


def _intelligence_hash(intelligence: dict) -> str:
    payload = json.dumps(intelligence, sort_keys=True, default=str, separators=(",", ":"))
    return make_cache_key("intelligence_payload", payload)


def run_analysis(intelligence: dict, trends: dict) -> dict:
    """Single-pass pipeline with explicit model responsibilities."""
    logger.info("Starting simplified pipeline (GPT gap/report + Gemini posts)...")

    brand_username = _extract_brand_username(intelligence)
    primary_trend = _pick_primary_trend(trends)
    major_trends = trends.get("major_trends", [])
    if not isinstance(major_trends, list):
        major_trends = [str(major_trends)]

    gap_context = build_gap_context(intelligence, trends)
    post_context = build_post_context(intelligence)
    strategy_context = build_strategy_context(intelligence, trends)

    tasks = {
        "gap": lambda: _layer_gap_gpt(gap_context, brand_username),
        "posts": lambda: _layer_posts_gemini(post_context, brand_username, primary_trend, major_trends),
        "report": lambda: _layer_report_gpt(strategy_context, brand_username),
    }

    outputs: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(fn): name for name, fn in tasks.items()}
        for future in as_completed(futures):
            name = futures[future]
            outputs[name] = future.result()
            logger.info("  %s done", name)

    gap = _parse_and_validate(outputs["gap"], GapAnalysis)
    posts = _parse_and_validate(outputs["posts"], PostPromptList)
    report = _parse_and_validate(outputs["report"], StrategyReport)

    final = MasterReport(
        gap_analysis=gap,
        post_prompts=posts,
        strategy_report=report,
        councilor_notes=(
            f"Pipeline mode: no council. "
            f"Gap + report model: GPT-OSS. "
            f"Post model: Gemini Flash. "
            f"Primary trend: {primary_trend}."
        ),
    )
    return final.model_dump()


def regenerate_post_prompts(intelligence: dict, trends: dict, selected_trend: str) -> dict:
    """Regenerate only post prompts with Gemini based on selected trend."""
    if not selected_trend or not selected_trend.strip():
        raise ValueError("selected_trend is required for post regeneration.")

    trend_label = selected_trend.strip()
    brand_username = _extract_brand_username(intelligence)
    competitor_usernames = sorted([u for u, d in intelligence.items() if not d.get("is_brand")])
    intelligence_hash = _intelligence_hash(intelligence)

    regen_cache_key = make_cache_key(
        "regen_posts",
        brand_username,
        frozenset(competitor_usernames),
        trend_label,
        intelligence_hash,
    )
    cached = _REGEN_CACHE.get(regen_cache_key)
    if cached is not None:
        return cached

    context = build_post_context(intelligence)
    major_trends = trends.get("major_trends", [])
    if not isinstance(major_trends, list):
        major_trends = [str(major_trends)]

    raw = _layer_posts_gemini(
        context=context,
        brand_username=brand_username,
        primary_trend=trend_label,
        major_trends=major_trends,
    )
    parsed = _parse_and_validate(raw, PostPromptList)

    payload = parsed.model_dump()
    payload["_meta"] = {
        "selected_trend": trend_label,
        "major_trends": major_trends,
        "regenerated_at": datetime.now().isoformat(),
    }
    _REGEN_CACHE[regen_cache_key] = payload
    return payload
