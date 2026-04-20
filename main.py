"""Entry point for the content strategy agent.

Usage:
    python main.py
"""
from __future__ import annotations

import json
from pprint import pprint

from orchestrator.graph import build_graph


def run_demo() -> None:
    app = build_graph()

    initial_state = {
        "primary_ig_url": "https://instagram.com/your_handle",
        "competitor_ig_urls": [
            "https://instagram.com/competitor_one",
            "https://instagram.com/competitor_two",
        ],
        "errors": [],
    }

    result = app.invoke(initial_state)

    if result.get("errors"):
        print("\n=== Errors ===")
        pprint(result["errors"])
        return

    print("=== Final Recommendations ===")
    recs = result.get("final_recommendations", {})
    print(json.dumps(recs, indent=2, default=str))


if __name__ == "__main__":
    run_demo()
