from __future__ import annotations

from pydantic import BaseModel, Field


class StrategyRequest(BaseModel):
    brand_url: str = Field(..., description="Instagram URL for the brand")
    competitor_urls: list[str] = Field(default_factory=list)


class TrendRegenerateRequest(BaseModel):
    brand_url: str
    competitor_urls: list[str] = Field(default_factory=list)
    selected_trend: str


class StrategyResponse(BaseModel):
    strategic_report: dict
    gap_analysis: dict
    post_prompts: list[dict]
    councilor_notes: dict
    market_trends: list[str]
    run_duration_seconds: float


class RegenerateResponse(BaseModel):
    post_prompts: list[dict]


class HealthResponse(BaseModel):
    status: str
    version: str
