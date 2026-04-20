"""LangGraph workflow builder.

Pipeline (5 nodes, merged search+trends):
  START → validate_input → scrape_instagram_data → fetch_market_trends →
  run_analysis → generate_recommendations → END

Every node transition has an error guard — if a node appends to
state["errors"], the graph short-circuits to END.
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agents import (
    fetch_market_trends_node,
    generate_recommendations_node,
    run_analysis_node,
    scrape_instagram_data_node,
    validate_input_node,
)
from orchestrator.state import ContentStrategyState


def _route_on_errors(state: ContentStrategyState) -> str:
    """Universal error guard — stop pipeline if any node reports errors."""
    if state.get("errors"):
        return "end"
    return "continue"


def build_graph():
    """Build and compile the LangGraph workflow."""
    graph = StateGraph(ContentStrategyState)

    # Register nodes
    graph.add_node("validate_input", validate_input_node)
    graph.add_node("scrape_instagram_data", scrape_instagram_data_node)
    graph.add_node("fetch_market_trends", fetch_market_trends_node)
    graph.add_node("run_analysis", run_analysis_node)
    graph.add_node("generate_recommendations", generate_recommendations_node)

    # Wire edges with error guards on every transition
    graph.add_edge(START, "validate_input")

    graph.add_conditional_edges(
        "validate_input",
        _route_on_errors,
        {"continue": "scrape_instagram_data", "end": END},
    )
    graph.add_conditional_edges(
        "scrape_instagram_data",
        _route_on_errors,
        {"continue": "fetch_market_trends", "end": END},
    )
    graph.add_conditional_edges(
        "fetch_market_trends",
        _route_on_errors,
        {"continue": "run_analysis", "end": END},
    )
    graph.add_conditional_edges(
        "run_analysis",
        _route_on_errors,
        {"continue": "generate_recommendations", "end": END},
    )
    graph.add_edge("generate_recommendations", END)

    return graph.compile()
