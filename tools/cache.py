from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from diskcache import Cache

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = PROJECT_ROOT / ".cache"
CACHE = Cache(str(CACHE_DIR))

APIFY_TTL = 21600
SERP_TTL = 21600
TRENDS_TTL = 43200
REGEN_TTL = None


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _normalize(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, set):
        return sorted(_normalize(v) for v in value)
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    return value


def make_cache_key(*args: Any) -> str:
    normalized = _normalize(args)
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return digest


def cache_get(key: str) -> Any | None:
    return CACHE.get(key, default=None)


def cache_set(key: str, value: Any, ttl_seconds: int | None) -> Any:
    if ttl_seconds is None:
        CACHE.set(key, value)
    else:
        CACHE.set(key, value, expire=ttl_seconds)
    return value
