from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from agents.analyzer import regenerate_post_prompts
from api.dependencies import get_pipeline_graph
from api.models import RegenerateResponse, StrategyRequest, StrategyResponse, TrendRegenerateRequest

router = APIRouter(prefix="/api", tags=["strategy"])


def _initial_state(brand_url: str, competitor_urls: list[str], progress_callback=None) -> dict[str, Any]:
    state = {
        "primary_ig_url": brand_url,
        "competitor_ig_urls": competitor_urls,
        "errors": [],
    }
    if progress_callback:
        # Optional callback hook for future node-level progress updates.
        state["progress_callback"] = progress_callback
    return state


def _extract_post_prompts(recommendations: dict[str, Any]) -> list[dict]:
    prompts = recommendations.get("post_prompts", [])
    if isinstance(prompts, dict):
        posts = prompts.get("posts", [])
        return posts if isinstance(posts, list) else []
    return prompts if isinstance(prompts, list) else []


def _extract_market_trends(result: dict[str, Any]) -> list[str]:
    available = result.get("available_trends", [])
    if isinstance(available, list):
        return [str(item) for item in available]

    trend_payload = result.get("market_trends", {})
    if isinstance(trend_payload, dict):
        queries = trend_payload.get("search_queries", [])
        if isinstance(queries, list):
            return [str(item) for item in queries]
    return []


def _extract_strategy_report(recommendations: dict[str, Any]) -> dict:
    report = recommendations.get("strategy_report", {})

    def _empty() -> dict[str, Any]:
        return {
            "executiveSummary": "",
            "top3Fixes": [],
            "doubleDownOn": [],
            "thirtyDayPlan": [],
        }

    def _to_list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    if isinstance(report, dict):
        return {
            "executiveSummary": str(
                report.get("executiveSummary")
                or report.get("executive_summary")
                or report.get("summary")
                or ""
            ),
            "top3Fixes": _to_list(report.get("top3Fixes") or report.get("top_3_fixes")),
            "doubleDownOn": _to_list(report.get("doubleDownOn") or report.get("double_down_on")),
            "thirtyDayPlan": _to_list(report.get("thirtyDayPlan") or report.get("30_day_plan")),
        }

    if isinstance(report, str):
        return {
            "executiveSummary": report,
            "top3Fixes": [],
            "doubleDownOn": [],
            "thirtyDayPlan": [],
        }

    return _empty()


def _extract_councilor_notes(recommendations: dict[str, Any]) -> dict:
    notes = recommendations.get("councilor_notes", {})
    if isinstance(notes, dict):
        return notes
    if isinstance(notes, list):
        return {"notes": notes}
    if isinstance(notes, str):
        return {"notes": notes}
    return {}


def _to_strategy_response(result: dict[str, Any], duration_seconds: float) -> StrategyResponse:
    recommendations = result.get("final_recommendations", {})
    if not isinstance(recommendations, dict):
        recommendations = {}

    return StrategyResponse(
        strategic_report=_extract_strategy_report(recommendations),
        gap_analysis=recommendations.get("gap_analysis", {}),
        post_prompts=_extract_post_prompts(recommendations),
        councilor_notes=_extract_councilor_notes(recommendations),
        market_trends=_extract_market_trends(result),
        run_duration_seconds=duration_seconds,
    )


@router.post("/strategy", response_model=StrategyResponse)
async def generate_strategy(
    request: StrategyRequest,
    graph=Depends(get_pipeline_graph),
) -> StrategyResponse:
    started = time.perf_counter()
    state = _initial_state(request.brand_url, request.competitor_urls)

    try:
        result = await asyncio.to_thread(graph.invoke, state)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if result.get("errors"):
        raise HTTPException(status_code=500, detail="; ".join(result["errors"]))

    duration = round(time.perf_counter() - started, 3)
    return _to_strategy_response(result, duration)


@router.post("/strategy/regenerate", response_model=RegenerateResponse)
async def regenerate_strategy_posts(
    request: TrendRegenerateRequest,
    graph=Depends(get_pipeline_graph),
) -> RegenerateResponse:
    base_state = _initial_state(request.brand_url, request.competitor_urls)

    try:
        result = await asyncio.to_thread(graph.invoke, base_state)
        if result.get("errors"):
            raise RuntimeError("; ".join(result["errors"]))

        intelligence = result.get("apify_brand_intelligence", {})
        trends = result.get("market_trends", {})
        regenerated = await asyncio.to_thread(
            regenerate_post_prompts,
            intelligence,
            trends,
            request.selected_trend,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    prompts = regenerated.get("posts", []) if isinstance(regenerated, dict) else []
    return RegenerateResponse(post_prompts=prompts if isinstance(prompts, list) else [])


@router.get("/strategy/stream")
async def stream_strategy(
    brand_url: str = Query(...),
    competitor_urls: str = Query(""),
    graph=Depends(get_pipeline_graph),
) -> StreamingResponse:
    competitor_list = [item.strip() for item in competitor_urls.split(",") if item.strip()]

    async def event_stream() -> AsyncGenerator[str, None]:
        progress_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        def progress_callback(stage: str, message: str, progress: int) -> None:
            payload = {"stage": stage, "message": message, "progress": progress}
            try:
                progress_queue.put_nowait(payload)
            except Exception:
                pass

        state = _initial_state(brand_url, competitor_list, progress_callback=progress_callback)
        started = time.perf_counter()

        stages = [
            {"stage": "scraping", "message": "Scraping Instagram profiles...", "progress": 20},
            {"stage": "trends", "message": "Fetching market trends...", "progress": 40},
            {"stage": "analyzing", "message": "Running gap analysis...", "progress": 70},
            {"stage": "generating", "message": "Generating post briefs...", "progress": 90},
        ]

        task = asyncio.create_task(asyncio.to_thread(graph.invoke, state))
        stage_index = 0

        try:
            while not task.done():
                while not progress_queue.empty():
                    queued = await progress_queue.get()
                    yield f"data: {json.dumps(queued)}\n\n"

                if stage_index < len(stages):
                    yield f"data: {json.dumps(stages[stage_index])}\n\n"
                    stage_index += 1

                await asyncio.sleep(0.8)

            result = await task
            if result.get("errors"):
                raise RuntimeError("; ".join(result["errors"]))

            duration = round(time.perf_counter() - started, 3)
            response_payload = _to_strategy_response(result, duration).model_dump()
            complete = {"stage": "complete", "payload": response_payload, "progress": 100}
            yield f"data: {json.dumps(complete)}\n\n"
        except Exception as exc:
            error_payload = {
                "stage": "error",
                "message": str(exc),
                "progress": 100,
            }
            yield f"data: {json.dumps(error_payload)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
