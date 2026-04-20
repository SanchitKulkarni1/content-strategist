# Content Strategy Agent (LangGraph Skeleton)

This project is a **multi-agent LangGraph skeleton** for Instagram content strategy.

## Pipeline

1. Input layer (your IG + competitor IG URLs)
2. Scraping layer (Apify)
3. Market trend layer (SERP + LLM intelligence)
4. Analysis layer (LLM)
5. Output layer (post ideas, captions, hashtags, best time)

## Project Structure

- `orchestrator/state.py`: Graph state schema
- `agents/`: Node functions (agents/tools)
- `orchestrator/graph.py`: LangGraph workflow definition
- `main.py`: Entry point

## Quick Start

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

2. Run:

```bash
python main.py
```

## Next Integrations

- Replace stub functions in `agents/scraping.py` with Apify client calls.
- Replace `agents/market_trend.py` with SERP API + LLM intelligence.
- Replace analysis and output nodes with your preferred LLM provider calls.
