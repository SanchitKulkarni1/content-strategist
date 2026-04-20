"""Analysis pipeline with LLM Council (GPT-OSS-12B + Gemini).

Layer 1: Gap Analysis          — Council (parallel GPT-OSS-12B + Gemini → Gemini chairman)
Layer 2: Post Prompts          — Council
Layer 3: Strategy Report       — Single GPT-OSS-12B call

All prompts are NICHE-AGNOSTIC: the LLM infers the domain, audience,
and tone entirely from the scraped Apify + SERP data.
"""
from __future__ import annotations

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from openai import OpenAI
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from agents.schemas import GapAnalysis, PostPromptList

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# ─────────────────────────────────────────────
# CLIENTS
# ─────────────────────────────────────────────

gpt_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

GPT_MODEL = "openai/gpt-oss-120b:free"
GEMINI_MODEL = "gemini-flash-latest"

# ─────────────────────────────────────────────
# BASE LLM CALLERS
# ─────────────────────────────────────────────

def _gpt(system: str, user: str, temperature: float = 0.7) -> str:
    """GPT-OSS-12B call — fast, data-driven. Returns JSON string."""
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
    """GPT-OSS-12B call — plain text response (no JSON mode)."""
    response = gpt_client.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


def _gemini(system: str, user: str, temperature: float = 0.7) -> str:
    """Gemini call — nuanced, creative. Uses system_instruction for proper role separation."""
    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            response_mime_type="application/json",
        ),
    )
    return response.text.strip()


def _gemini_structured(
    system: str,
    user: str,
    schema: type[BaseModel],
    temperature: float = 0.7,
) -> str:
    """Gemini call with Pydantic schema enforcement."""
    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    return response.text.strip()


def _parse_and_validate(raw: str, schema: type[BaseModel], retries: int = 2) -> BaseModel:
    """Parse raw JSON text and validate against a Pydantic schema.
    
    Retries by stripping markdown fences and common LLM artifacts.
    """
    import re

    for attempt in range(retries + 1):
        try:
            # Strip markdown code fences if present
            cleaned = re.sub(r"```json\s*|```\s*", "", raw).strip()
            return schema.model_validate_json(cleaned)
        except (ValidationError, json.JSONDecodeError) as exc:
            if attempt < retries:
                logger.warning(
                    f"  Parse attempt {attempt + 1} failed: {exc}. Retrying..."
                )
                # Try extracting first JSON object/array from the text
                match = re.search(r"[\[{]", cleaned)
                if match:
                    raw = cleaned[match.start():]
                continue
            logger.error(f"  All parse attempts failed for {schema.__name__}: {exc}")
            raise


# ─────────────────────────────────────────────
# LLM COUNCIL
# ─────────────────────────────────────────────

def _council(
    system: str,
    user: str,
    schema: type[BaseModel] | None = None,
    temperature: float = 0.7,
) -> str:
    """LLM Council Pattern:
    1. GPT-OSS-12B + Gemini respond to the same prompt in PARALLEL
    2. Gemini acts as Chairman to synthesize the best merged response
    """
    logger.info("  [Council] Firing GPT-OSS-12B + Gemini in parallel...")

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_gpt    = executor.submit(_gpt, system, user, temperature)
        future_gemini = executor.submit(_gemini, system, user, temperature)
        response_a = future_gpt.result()
        response_b = future_gemini.result()

    logger.info("  [Council] Both responses received. Gemini chairman merging...")

    merge_system = (
        "You are the Chairman of an expert LLM Council. "
        "Two AI analysts have independently analyzed the same data. "
        "Synthesize ONE final response taking the SHARPEST, most SPECIFIC, "
        "most ACTIONABLE insights from both."
    )

    merge_user = f"""Two expert AI models analyzed the same data independently.
Your job: synthesize ONE final response.

Rules:
- Pick the BEST, most data-backed insight from each — do NOT average weakly
- If both agree → include with higher confidence
- If they disagree → pick the more specific, evidence-backed one
- Keep EXACTLY the same JSON structure as the inputs
- Return ONLY valid JSON, no explanation

=== RESPONSE A (GPT-OSS-12B — data-driven) ===
{response_a}

=== RESPONSE B (Gemini — creative/nuanced) ===
{response_b}

Merged final response:"""

    # Gemini as chairman — better at nuanced synthesis
    if schema:
        return _gemini_structured(merge_system, merge_user, schema, temperature=0.3)
    return _gemini(merge_system, merge_user, temperature=0.3)


# ─────────────────────────────────────────────
# CONTEXT BUILDER
# ─────────────────────────────────────────────

def _build_context(intelligence: dict, trends: dict) -> str:
    """Builds a rich combined context string from all scraped data.
    
    The context is niche-agnostic — the LLM will infer the domain,
    audience, and competitive landscape from the data itself.
    """
    brand_uname = next(
        (u for u, d in intelligence.items() if d.get("is_brand")),
        None,
    )
    if not brand_uname:
        raise ValueError("No brand account found in intelligence data (no is_brand=True).")

    brand = intelligence[brand_uname]
    competitors = {u: d for u, d in intelligence.items() if not d.get("is_brand")}

    # Brand section
    bp = brand["profile"]
    ba = brand["analytics"]
    brand_captions = [
        p["caption"][:120] for p in brand["posts"] if p.get("caption")
    ][:5]

    # Competitor section
    comp_blocks = []
    for uname, data in competitors.items():
        a = data["analytics"]
        pinned_caption = next(
            (p["caption"][:100] for p in data["posts"] if p.get("is_pinned")),
            "None",
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

    # SERP trend signals
    trend_snippets = []
    for query, results in trends.get("serp_results", {}).items():
        for r in results[:2]:
            if r.get("snippet"):
                trend_snippets.append(
                    f"  [{query[:60]}]\n  → {r['snippet'][:150]}"
                )

    today = datetime.now().strftime("%B %Y")

    context = f"""
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
{chr(10).join(f'  - {q}' for q in trends.get('gemini_queries', []))}

Analysis Date: {today}
""".strip()

    return context


# ─────────────────────────────────────────────
# LAYER 1: GAP ANALYSIS (Council)
# ─────────────────────────────────────────────

def analyze_gaps(context: str, brand_username: str) -> GapAnalysis:
    """Council decides: where is the brand strong, where is it weak?
    
    Prompts are data-driven — the LLM infers the niche, audience,
    and competitive landscape entirely from the context.
    """
    logger.info("Layer 1: Gap Analysis [Council Mode]")

    system = """You are a senior social media strategist and competitive analyst.
You are given detailed Instagram profile data, post analytics, and market trend signals
for a brand and its competitors.

Your job:
1. INFER the brand's niche, target audience, and market positioning from the data
2. Analyze strengths, weaknesses, and competitive gaps
3. Identify market opportunities from the trend signals
4. Every insight MUST be tied directly to specific data points — no generic advice

Think step by step:
- What industry/niche is this brand in? (infer from bio, hashtags, captions, content mix)
- Who is the target audience? (infer from content style, engagement patterns)
- Where does the brand outperform competitors? Where does it fall short?
- What trending opportunities can the brand capitalize on?"""

    user = f"""Analyze this competitive intelligence data for @{brand_username}:

{context}

Return a JSON object with this structure:
- overall_score: brand_rating (1-10), vs_competitors (summary)
- strengths: list of {{area, evidence, score}}
- weaknesses: list of {{area, evidence, impact}}
- competitor_advantages: list of {{competitor, advantage, how_to_counter}}
- quick_wins: list of {{action, expected_impact, effort}}
- market_opportunities: list of {{opportunity, trend_signal, urgency}}"""

    raw = _council(system, user, schema=GapAnalysis, temperature=0.4)
    return _parse_and_validate(raw, GapAnalysis)


# ─────────────────────────────────────────────
# LAYER 2: POST PROMPTS (Council)
# ─────────────────────────────────────────────

def generate_post_prompts(
    context: str,
    gap_analysis: GapAnalysis,
    brand_username: str,
) -> PostPromptList:
    """Council generates 5 ready-to-shoot content briefs.
    Each targets a specific gap or opportunity.
    
    The LLM infers the right tone, aesthetics, cultural context,
    and audience from the data — no hardcoded niche assumptions.
    """
    logger.info("Layer 2: Post Prompts [Council Mode]")

    gaps_summary = json.dumps({
        "weaknesses":           [w.model_dump() for w in gap_analysis.weaknesses],
        "market_opportunities": [m.model_dump() for m in gap_analysis.market_opportunities],
        "quick_wins":           [q.model_dump() for q in gap_analysis.quick_wins],
    }, indent=2)

    system = """You are a creative director specializing in Instagram content strategy.
You are given competitive intelligence data and a gap analysis for a brand.

Your job:
1. INFER the brand's niche, visual style, and target audience from the data
2. Create content briefs that are culturally relevant to the brand's market
3. Each brief must target a SPECIFIC gap or opportunity from the analysis
4. Briefs must be immediately actionable — a creator should be able to shoot from them
5. Every recommendation must be better than what competitors are currently doing

Think about:
- What content format works best for this niche? (Reels, Carousels, Static)
- What visual aesthetics match the brand's positioning?
- What posting times optimize for this audience's timezone and behavior?
- What hooks will stop the scroll for THIS specific audience?"""

    user = f"""Create 5 Instagram post prompts for @{brand_username}.

COMPETITIVE INTELLIGENCE:
{context}

GAP ANALYSIS:
{gaps_summary}

For each post, provide:
- post_number, gap_addressed, format (Reel/Carousel/Static Image)
- hook (scroll-stopping opener), concept (full visual direction)
- caption (ready to post with emojis), hashtags (list)
- call_to_action, posting_time, why_this_wins

Return as a JSON object with a "posts" key containing an array of 5 post objects."""

    raw = _council(system, user, schema=PostPromptList, temperature=0.85)
    return _parse_and_validate(raw, PostPromptList)


# ─────────────────────────────────────────────
# LAYER 3: STRATEGY REPORT (GPT-OSS-12B — summarizing)
# ─────────────────────────────────────────────

def generate_strategy_report(
    context: str,
    gap_analysis: GapAnalysis,
    brand_username: str,
) -> str:
    """One-page strategic brief for the founder.
    
    Single GPT-OSS-12B call — council is overkill for summarization.
    The LLM infers the niche and tailors the brief accordingly.
    """
    logger.info("Layer 3: Strategy Report [GPT-OSS-12B]")

    system = """You are a brand consultant writing a concise strategic brief.
Analyze the data to understand the brand's industry, market, and competitive position.
Write in clear, direct language. Every sentence must be actionable or insightful. No fluff.
Tailor your advice to the specific niche and audience you observe in the data."""

    user = f"""Write a concise strategic brief (max 500 words) for @{brand_username}.

KEY GAPS:
{json.dumps([w.model_dump() for w in gap_analysis.weaknesses], indent=2)}

KEY OPPORTUNITIES:
{json.dumps([m.model_dump() for m in gap_analysis.market_opportunities], indent=2)}

QUICK WINS:
{json.dumps([q.model_dump() for q in gap_analysis.quick_wins], indent=2)}

OVERALL SCORE:
{gap_analysis.overall_score.model_dump()}

Structure exactly as:
1. EXECUTIVE SUMMARY (2-3 sentences: current state, biggest gap, biggest opportunity)
2. WHERE YOU STAND VS COMPETITORS
3. TOP 3 THINGS TO FIX IMMEDIATELY (with specific action for each)
4. TOP 3 THINGS TO DOUBLE DOWN ON (what's already working)
5. 30-DAY ACTION PLAN (week-by-week breakdown)"""

    return _gpt_text(system, user, temperature=0.5)


# ─────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────

def run_analysis(intelligence: dict, trends: dict) -> dict:
    """Full 3-layer analysis pipeline:
    Layer 1 → Gap Analysis        (LLM Council)
    Layer 2 → Post Prompts        (LLM Council)
    Layer 3 → Strategy Report     (GPT-OSS-12B)
    """
    logger.info("Starting full analysis pipeline...")

    brand_username = next(
        (u for u, d in intelligence.items() if d.get("is_brand")),
        None,
    )
    if not brand_username:
        raise ValueError("No brand account found in intelligence data.")

    context = _build_context(intelligence, trends)
    gap_analysis = analyze_gaps(context, brand_username)
    post_prompts = generate_post_prompts(context, gap_analysis, brand_username)
    strategy_report = generate_strategy_report(context, gap_analysis, brand_username)

    return {
        "gap_analysis":     gap_analysis.model_dump(),
        "post_prompts":     post_prompts.model_dump(),
        "strategy_report":  strategy_report,
    }