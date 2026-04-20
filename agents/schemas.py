"""Pydantic schemas for structured LLM outputs.

Used by both Gemini (response_schema) and Cerebras (json_schema)
to enforce consistent, parseable responses from the LLM council.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# GAP ANALYSIS SCHEMA  (Layer 1)
# ─────────────────────────────────────────────

class OverallScore(BaseModel):
    brand_rating: int = Field(
        description="Overall Instagram presence score from 1 to 10."
    )
    vs_competitors: str = Field(
        description="One-line summary of how the brand stacks up against competitors."
    )


class Strength(BaseModel):
    area: str = Field(description="What the brand is doing well.")
    evidence: str = Field(description="Specific data point supporting this.")
    score: int = Field(description="Score from 1 to 10 for this strength.")


class Weakness(BaseModel):
    area: str = Field(description="What the brand is lacking.")
    evidence: str = Field(description="Specific data point supporting this.")
    impact: str = Field(description="Impact level: high, medium, or low.")


class CompetitorAdvantage(BaseModel):
    competitor: str = Field(description="Competitor @username.")
    advantage: str = Field(description="What they do better.")
    how_to_counter: str = Field(description="Specific action to counter this.")


class QuickWin(BaseModel):
    action: str = Field(description="Specific, immediately actionable step.")
    expected_impact: str = Field(description="What result to expect.")
    effort: str = Field(description="Effort level: low, medium, or high.")


class MarketOpportunity(BaseModel):
    opportunity: str = Field(description="The opportunity to seize.")
    trend_signal: str = Field(description="Evidence from SERP/trend data.")
    urgency: str = Field(description="Urgency level: high, medium, or low.")


class GapAnalysis(BaseModel):
    overall_score: OverallScore
    strengths: list[Strength]
    weaknesses: list[Weakness]
    competitor_advantages: list[CompetitorAdvantage]
    quick_wins: list[QuickWin]
    market_opportunities: list[MarketOpportunity]


# ─────────────────────────────────────────────
# POST PROMPTS SCHEMA  (Layer 2)
# ─────────────────────────────────────────────

class PostPrompt(BaseModel):
    post_number: int = Field(description="Sequential post number (1-5).")
    gap_addressed: str = Field(
        description="Which weakness or opportunity this post targets."
    )
    format: str = Field(
        description="Post format: Reel, Carousel, or Static Image."
    )
    hook: str = Field(
        description="First 3 seconds / opening line that stops the scroll."
    )
    concept: str = Field(
        description="Full content concept — what to shoot, setting, mood, visual direction."
    )
    caption: str = Field(
        description="Full ready-to-post Instagram caption with emojis and line breaks."
    )
    hashtags: list[str] = Field(
        description="List of relevant hashtags without the # symbol."
    )
    call_to_action: str = Field(
        description="What you want the viewer to do next."
    )
    posting_time: str = Field(
        description="Best day + time window to post for maximum reach."
    )
    why_this_wins: str = Field(
        description="Why this outperforms what competitors are currently doing."
    )


class PostPromptList(BaseModel):
    posts: list[PostPrompt] = Field(
        description="List of 5 Instagram post prompts."
    )
