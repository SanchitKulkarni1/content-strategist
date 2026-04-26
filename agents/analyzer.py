"""Analysis pipeline with LLM Council (GPT-OSS-12B + Claude Sonnet → Claude Opus).

Phase 1 — ALL THREE LAYERS run fully in parallel:
  L1: Gap Analysis      — GPT + Sonnet in parallel (no internal merge)
  L2: Post Prompts      — GPT + Sonnet in parallel (no internal merge)
  L3: Strategy Report   — GPT + Sonnet in parallel (no internal merge)

Phase 2 — Single Opus call:
  Receives all 6 raw outputs, synthesizes ONE master report with
  validated gap analysis, post prompts, and strategic brief.

Total LLM calls : 6 in parallel → 1 Opus call = 2 phases
Target wall time : < 2 minutes
"""
from __future__ import annotations

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import anthropic
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

from agents.schemas import GapAnalysis, PostPromptList, MasterReport

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


# ─────────────────────────────────────────────
# CLIENTS
# ─────────────────────────────────────────────

gpt_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

GPT_MODEL      = "openai/gpt-oss-120b:free"
ANALYSIS_AGENT = "claude-sonnet-4-6"   # Phase 1 worker — all 6 parallel calls
COUNCILOR      = "claude-opus-4-7"     # Phase 2 chairman — single synthesis call


# ─────────────────────────────────────────────
# BASE LLM CALLERS
# ─────────────────────────────────────────────

def _gpt(system: str, user: str, temperature: float = 0.7) -> str:
    """GPT-OSS call — JSON mode."""
    response = gpt_client.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content.strip()


def _gpt_text(system: str, user: str, temperature: float = 0.7) -> str:
    """GPT-OSS call — plain text."""
    response = gpt_client.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


def _sonnet(system: str, user: str, temperature: float = 0.7) -> str:
    """Claude Sonnet call — JSON mode via prompt instruction."""
    return anthropic_client.messages.create(
        model=ANALYSIS_AGENT,
        max_tokens=8192,
        temperature=temperature,
        system=system + "\n\nRespond with ONLY valid JSON. No explanation, no markdown fences.",
        messages=[{"role": "user", "content": user}],
    ).content[0].text.strip()


def _sonnet_text(system: str, user: str, temperature: float = 0.7) -> str:
    """Claude Sonnet call — plain text."""
    return anthropic_client.messages.create(
        model=ANALYSIS_AGENT,
        max_tokens=8192,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": user}],
    ).content[0].text.strip()


def _parse_and_validate(raw: str, schema: type[BaseModel], retries: int = 2) -> BaseModel:
    """Parse raw JSON and validate against a Pydantic schema with retry."""
    import re
    for attempt in range(retries + 1):
        try:
            cleaned = re.sub(r"```json\s*|```\s*", "", raw).strip()
            return schema.model_validate_json(cleaned)
        except (ValidationError, json.JSONDecodeError) as exc:
            if attempt < retries:
                logger.warning(f"  Parse attempt {attempt + 1} failed: {exc}. Retrying...")
                match = re.search(r"[\[{]", cleaned)
                if match:
                    raw = cleaned[match.start():]
                continue
            logger.error(f"  All parse attempts failed for {schema.__name__}: {exc}")
            raise


# ─────────────────────────────────────────────
# CONTEXT BUILDER
# ─────────────────────────────────────────────

def _build_context(intelligence: dict, trends: dict) -> str:
    brand_uname = next(
        (u for u, d in intelligence.items() if d.get("is_brand")), None
    )
    if not brand_uname:
        raise ValueError("No brand account found in intelligence data (no is_brand=True).")

    brand       = intelligence[brand_uname]
    competitors = {u: d for u, d in intelligence.items() if not d.get("is_brand")}

    bp = brand["profile"]
    ba = brand["analytics"]
    brand_captions = [p["caption"][:120] for p in brand["posts"] if p.get("caption")][:5]

    comp_blocks = []
    for uname, data in competitors.items():
        a = data["analytics"]
        pinned_caption = next(
            (p["caption"][:100] for p in data["posts"] if p.get("is_pinned")), "None"
        )
        comp_blocks.append(f"""
  @{uname}
  Followers    : {data['profile'].get('followers', 'N/A')}
  Avg Likes    : {a.get('avg_likes')} | Avg Comments: {a.get('avg_comments')}
  Content Mix  : {a.get('content_type_mix')}
  Top Hashtags : {a.get('all_hashtags_used', [])[:8]}
  Collabs      : {a.get('influencer_collabs', [])}
  Pinned Post  : {pinned_caption}
""")

    trend_snippets = []
    for query, results in trends.get("serp_results", {}).items():
        for r in results[:2]:
            if r.get("snippet"):
                trend_snippets.append(f"  [{query[:60]}]\n  → {r['snippet'][:150]}")

    return f"""
╔══════════════════════════════════════╗
║      BRAND UNDER ANALYSIS            ║
╚══════════════════════════════════════╝
@{brand_uname}
Followers    : {bp.get('followers', 'N/A')}
Bio          : {bp.get('bio', 'N/A')}
Avg Likes    : {ba.get('avg_likes')} | Avg Comments: {ba.get('avg_comments')}
Content Mix  : {ba.get('content_type_mix')}
Top Hashtags : {ba.get('all_hashtags_used', [])[:8]}
Collabs      : {ba.get('influencer_collabs', [])}
Recent Captions:
{chr(10).join(f'  - {c}' for c in brand_captions)}

╔══════════════════════════════════════╗
║           COMPETITORS                ║
╚══════════════════════════════════════╝
{"".join(comp_blocks)}

╔══════════════════════════════════════╗
║       MARKET TREND SIGNALS           ║
╚══════════════════════════════════════╝
{chr(10).join(trend_snippets[:10])}

Search queries used:
{chr(10).join(f'  - {q}' for q in trends.get('search_queries', []))}

Analysis Date: {datetime.now().strftime("%B %Y")}
""".strip()


def _extract_brand_username(intelligence: dict) -> str:
    """Return the brand username from intelligence payload."""
    brand_username = next(
        (u for u, d in intelligence.items() if d.get("is_brand")), None
    )
    if not brand_username:
        raise ValueError("No brand account found in intelligence data.")
    return brand_username


def _selected_trend_context(selected_trend: str) -> str:
    """Append hard constraints for trend-focused post generation."""
    return f"""
╔══════════════════════════════════════╗
║      ACTIVE TREND CONSTRAINT         ║
╚══════════════════════════════════════╝
Selected trend: {selected_trend}

Post generation rules:
- Every post must directly align with the selected trend.
- Hooks, concepts, captions, and hashtags should all reflect this trend.
- If a post cannot map to the trend, replace it with a different idea that can.
""".strip()


# ─────────────────────────────────────────────
# PHASE 1 — LAYER WORKERS (6 independent functions)
# Each returns a raw string (JSON or text).
# All 6 fire simultaneously in run_analysis().
# ─────────────────────────────────────────────

def _layer1_gap_gpt(context: str, brand_username: str) -> str:
    system = """You are a senior social media strategist and competitive analyst.
Infer the brand's niche, target audience, and market positioning from the data.
Analyze strengths, weaknesses, competitive gaps, and market opportunities.
Every insight MUST reference specific data points — no generic advice."""

    user = f"""Analyze competitive intelligence for @{brand_username}:

{context}

Return JSON:
- overall_score: {{brand_rating (1-10), vs_competitors}}
- strengths: [{{area, evidence, score}}]
- weaknesses: [{{area, evidence, impact}}]
- competitor_advantages: [{{competitor, advantage, how_to_counter}}]
- quick_wins: [{{action, expected_impact, effort}}]
- market_opportunities: [{{opportunity, trend_signal, urgency}}]"""

    return _gpt(system, user, temperature=0.4)


def _layer1_gap_sonnet(context: str, brand_username: str) -> str:
    system = """You are a senior social media strategist and competitive analyst.
Infer the brand's niche, target audience, and market positioning from the data.
Analyze strengths, weaknesses, competitive gaps, and market opportunities.
Every insight MUST reference specific data points — no generic advice."""

    user = f"""Analyze competitive intelligence for @{brand_username}:

{context}

Return JSON:
- overall_score: {{brand_rating (1-10), vs_competitors}}
- strengths: [{{area, evidence, score}}]
- weaknesses: [{{area, evidence, impact}}]
- competitor_advantages: [{{competitor, advantage, how_to_counter}}]
- quick_wins: [{{action, expected_impact, effort}}]
- market_opportunities: [{{opportunity, trend_signal, urgency}}]"""

    return _sonnet(system, user, temperature=0.4)


def _layer2_posts_gpt(context: str, brand_username: str) -> str:
    system = """You are a creative director specializing in Instagram content strategy.
Infer the brand's niche, visual style, and target audience from the data.
Create 5 content briefs targeting gaps or opportunities — immediately actionable."""

    user = f"""Create 5 Instagram post prompts for @{brand_username}.

{context}

Return JSON with "posts" array. Each post:
- post_number, gap_addressed, format (Reel/Carousel/Static Image)
- hook, concept, caption (with emojis), hashtags (list)
- call_to_action, posting_time, why_this_wins"""

    return _gpt(system, user, temperature=0.85)


def _layer2_posts_sonnet(context: str, brand_username: str) -> str:
    system = """You are a creative director specializing in Instagram content strategy.
Infer the brand's niche, visual style, and target audience from the data.
Create 5 content briefs targeting gaps or opportunities — immediately actionable."""

    user = f"""Create 5 Instagram post prompts for @{brand_username}.

{context}

Return JSON with "posts" array. Each post:
- post_number, gap_addressed, format (Reel/Carousel/Static Image)
- hook, concept, caption (with emojis), hashtags (list)
- call_to_action, posting_time, why_this_wins"""

    return _sonnet(system, user, temperature=0.85)


def _layer3_report_gpt(context: str, brand_username: str) -> str:
    system = """You are a brand consultant writing a concise strategic brief.
Write in clear, direct language. Every sentence must be actionable or insightful. No fluff."""

    user = f"""Write a strategic brief (max 500 words) for @{brand_username}.

{context}

Structure:
1. EXECUTIVE SUMMARY (2-3 sentences)
2. WHERE YOU STAND VS COMPETITORS
3. TOP 3 THINGS TO FIX IMMEDIATELY
4. TOP 3 THINGS TO DOUBLE DOWN ON
5. 30-DAY ACTION PLAN (week-by-week)"""

    return _gpt_text(system, user, temperature=0.5)


def _layer3_report_sonnet(context: str, brand_username: str) -> str:
    system = """You are a brand consultant writing a concise strategic brief.
Write in clear, direct language. Every sentence must be actionable or insightful. No fluff."""

    user = f"""Write a strategic brief (max 500 words) for @{brand_username}.

{context}

Structure:
1. EXECUTIVE SUMMARY (2-3 sentences)
2. WHERE YOU STAND VS COMPETITORS
3. TOP 3 THINGS TO FIX IMMEDIATELY
4. TOP 3 THINGS TO DOUBLE DOWN ON
5. 30-DAY ACTION PLAN (week-by-week)"""

    return _sonnet_text(system, user, temperature=0.5)


# ─────────────────────────────────────────────
# PHASE 2 — OPUS CHAIRMAN SYNTHESIS
# ─────────────────────────────────────────────

def _opus_synthesize(
    brand_username: str,
    gap_gpt: str,
    gap_sonnet: str,
    posts_gpt: str,
    posts_sonnet: str,
    report_gpt: str,
    report_sonnet: str,
) -> MasterReport:
    """Single Opus call — synthesizes all 6 Phase 1 outputs into one MasterReport."""
    logger.info("Phase 2: Opus chairman synthesizing all outputs...")

    schema_json = json.dumps(MasterReport.model_json_schema(), indent=2)

    system = f"""You are the Chairman of an expert LLM Council reviewing all analysis for @{brand_username}.
Six independent AI outputs are provided across three layers: gap analysis, post prompts, and strategy report.
Your job: synthesize ONE definitive master report that is sharper and more actionable than any single input.

Rules:
- Where models agree → include with high confidence
- Where models disagree → pick the more specific, evidence-backed position
- Eliminate all redundancy — the master report must be tighter than its inputs
- Every recommendation must be tied to a specific data point
- Return ONLY valid JSON matching this schema:
{schema_json}

CRITICAL TOKEN INSTRUCTION:
Because you are generating a massive JSON payload (analysis + 5 posts + strategy report), you risk hitting your output token limit. 
To prevent JSON truncation, you MUST:
1. Be extremely purely concise — use tight, punchy language.
2. Limit `strategy_report` to max 250 words total.
3. Keep `councilor_notes` under 3 sentences.
4. Eliminate all fluff."""

    user = f"""Synthesize these six outputs into ONE master report for @{brand_username}.

=== GAP ANALYSIS — GPT-OSS (data-driven) ===
{gap_gpt}

=== GAP ANALYSIS — Claude Sonnet (nuanced) ===
{gap_sonnet}

=== POST PROMPTS — GPT-OSS (data-driven) ===
{posts_gpt}

=== POST PROMPTS — Claude Sonnet (creative) ===
{posts_sonnet}

=== STRATEGY REPORT — GPT-OSS ===
{report_gpt}

=== STRATEGY REPORT — Claude Sonnet ===
{report_sonnet}"""

    raw = anthropic_client.messages.create(
        model=COUNCILOR,
        max_tokens=8192,
        system=system,
        messages=[{"role": "user", "content": user}],
    ).content[0].text.strip()

    return _parse_and_validate(raw, MasterReport)


# ─────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────

def run_analysis(intelligence: dict, trends: dict) -> dict:
    """Two-phase pipeline:

    Phase 1 — 6 workers fire simultaneously (max_workers=6):
        L1: gap_gpt,    gap_sonnet
        L2: posts_gpt,  posts_sonnet
        L3: report_gpt, report_sonnet

    Phase 2 — 1 Opus call synthesizes all 6 into MasterReport.

    Wall time = max(Phase 1 slowest worker) + Opus call
    """
    logger.info("Starting optimized 2-phase pipeline...")

    brand_username = _extract_brand_username(intelligence)

    context = _build_context(intelligence, trends)

    # ── Phase 1: all 6 workers in parallel ──────────────────────────────────
    logger.info("Phase 1: Firing all 6 layer workers in parallel...")

    tasks = {
        "gap_gpt":       lambda: _layer1_gap_gpt(context, brand_username),
        "gap_sonnet":    lambda: _layer1_gap_sonnet(context, brand_username),
        "posts_gpt":     lambda: _layer2_posts_gpt(context, brand_username),
        "posts_sonnet":  lambda: _layer2_posts_sonnet(context, brand_username),
        "report_gpt":    lambda: _layer3_report_gpt(context, brand_username),
        "report_sonnet": lambda: _layer3_report_sonnet(context, brand_username),
    }

    results: dict[str, str] = {}
    errors:  dict[str, str] = {}

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(fn): name for name, fn in tasks.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
                logger.info(f"  [Phase 1] {name} — done")
            except Exception as exc:
                errors[name] = str(exc)
                logger.warning(f"  [Phase 1] {name} — FAILED: {exc}")

    # Graceful fallback: if one model in a pair failed, use the other for both
    pairs = [
        ("gap_gpt",    "gap_sonnet"),
        ("posts_gpt",  "posts_sonnet"),
        ("report_gpt", "report_sonnet"),
    ]
    for a, b in pairs:
        if a not in results and b not in results:
            raise RuntimeError(f"Both workers failed for pair ({a}, {b}) — cannot proceed.")
        if a not in results:
            logger.warning(f"  Fallback: duplicating {b} → {a}")
            results[a] = results[b]
        if b not in results:
            logger.warning(f"  Fallback: duplicating {a} → {b}")
            results[b] = results[a]

    # ── Phase 2: single Opus synthesis ──────────────────────────────────────
    master = _opus_synthesize(
        brand_username,
        gap_gpt=results["gap_gpt"],
        gap_sonnet=results["gap_sonnet"],
        posts_gpt=results["posts_gpt"],
        posts_sonnet=results["posts_sonnet"],
        report_gpt=results["report_gpt"],
        report_sonnet=results["report_sonnet"],
    )

    logger.info("Pipeline complete.")
    return master.model_dump()


def regenerate_post_prompts(intelligence: dict, trends: dict, selected_trend: str) -> dict:
    """Regenerate only post prompts using a selected/custom trend."""
    if not selected_trend or not selected_trend.strip():
        raise ValueError("selected_trend is required for post regeneration.")

    trend_label = selected_trend.strip()
    brand_username = _extract_brand_username(intelligence)
    context = _build_context(intelligence, trends)
    context = f"{context}\n\n{_selected_trend_context(trend_label)}"

    logger.info("Regenerating post prompts for trend: %s", trend_label)
    # Keep regeneration path fast and deterministic: single Sonnet worker only.
    sonnet_raw = _layer2_posts_sonnet(context, brand_username)
    parsed = _parse_and_validate(sonnet_raw, PostPromptList)
    payload = parsed.model_dump()
    payload["_meta"] = {
        "selected_trend": trend_label,
        "regenerated_at": datetime.now().isoformat(),
    }
    return payload