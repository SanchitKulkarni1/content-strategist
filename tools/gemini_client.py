from __future__ import annotations

import threading
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types


def _load_api_keys() -> tuple[str, ...]:
    keys = [
        (os.getenv("GEMINI_API_KEY1") or "").strip(),
        (os.getenv("GEMINI_API_KEY2") or "").strip(),
        (os.getenv("GEMINI_API_KEY_1") or "").strip(),
        (os.getenv("GEMINI_API_KEY_2") or "").strip(),
        (os.getenv("GEMINI_API_KEY") or "").strip(),
        (os.getenv("GOOGLE_API_KEY") or "").strip(),
    ]
    deduped: list[str] = []
    seen: set[str] = set()
    for key in keys:
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(key)
    return tuple(deduped)


_INIT_LOCK = threading.Lock()
_CLIENT_LOCK = threading.Lock()
_CLIENT_CURSOR = 0
_CLIENTS: tuple[genai.Client, ...] | None = None


def _ensure_clients() -> tuple[genai.Client, ...]:
    global _CLIENTS
    if _CLIENTS is not None:
        return _CLIENTS

    with _INIT_LOCK:
        if _CLIENTS is not None:
            return _CLIENTS

        # Ensure API routes that do not explicitly load .env can still resolve keys.
        load_dotenv(override=False)
        api_keys = _load_api_keys()
        if not api_keys:
            raise RuntimeError(
                "No Gemini API keys found. Set GEMINI_API_KEY1 and GEMINI_API_KEY2 (or GEMINI_API_KEY/GOOGLE_API_KEY)."
            )

        _CLIENTS = tuple(genai.Client(api_key=key) for key in api_keys)
        return _CLIENTS


def _next_client() -> tuple[genai.Client, int]:
    global _CLIENT_CURSOR
    clients = _ensure_clients()
    with _CLIENT_LOCK:
        idx = _CLIENT_CURSOR % len(clients)
        _CLIENT_CURSOR += 1
    return clients[idx], idx + 1


def _response_text(response: object) -> str:
    text = (getattr(response, "text", "") or "").strip()
    if text:
        return text

    fragments: list[str] = []
    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        if content is None:
            continue
        for part in getattr(content, "parts", None) or []:
            part_text = getattr(part, "text", None)
            if part_text:
                fragments.append(str(part_text))

    merged = "\n".join(fragments).strip()
    if not merged:
        raise ValueError("Gemini returned an empty response.")
    return merged


def generate_gemini(
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_output_tokens: int = 8192,
    json_mode: bool = False,
) -> tuple[str, int]:
    """Generate text with Gemini using round-robin API-key balancing.

    Returns tuple(response_text, key_slot_index_starting_at_1).
    """
    client, key_slot = _next_client()

    config_kwargs: dict[str, object] = {
        "system_instruction": system_prompt,
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
    }
    if json_mode:
        config_kwargs["response_mime_type"] = "application/json"

    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(**config_kwargs),
    )
    return _response_text(response), key_slot
