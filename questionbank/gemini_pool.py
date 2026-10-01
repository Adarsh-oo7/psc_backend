"""Rotate the free Gemini projects without ever logging an API key.

Google applies the free quota per project, not per key. Extra keys inside
the same project do not add more quota. The keys live in a root-only file
on the server, or in GEMINI_API_KEYS, and are never written to the database.
"""
from __future__ import annotations

import json
import os
import re
import time

import requests
from django.utils import timezone

from .models import GeminiProjectUsage

KEYS_PATH = os.environ.get("GEMINI_KEYS_FILE", "/var/www/kpsc-backend/secrets/gemini_keys.json")
MODELS = [
    os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"),
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite",
]
# A gap between calls so one project stays under a typical free 10-per-minute limit.
CALL_GAP_SECONDS = 6


def _redact(text: str) -> str:
    cleaned = re.sub(r"key=[^&\s]+", "key=REDACTED", text or "")
    cleaned = re.sub(r"AQ\.[A-Za-z0-9_\-]+", "REDACTED", cleaned)
    return cleaned[:240]


def load_keys() -> list[dict]:
    """Return [{project, key}, ...] from the secrets file or the environment."""
    raw = ""
    if os.path.exists(KEYS_PATH):
        with open(KEYS_PATH, "r", encoding="utf-8") as handle:
            raw = handle.read()
    elif os.environ.get("GEMINI_API_KEYS"):
        raw = os.environ["GEMINI_API_KEYS"]
    elif os.environ.get("GEMINI_API_KEY"):
        return [{"project": "default", "key": os.environ["GEMINI_API_KEY"]}]
    else:
        return []

    raw = raw.strip()
    if not raw:
        return []
    if raw.startswith("["):
        rows = json.loads(raw)
    else:
        rows = []
        for part in raw.split(","):
            project, _, key = part.partition(":")
            if key:
                rows.append({"project": project.strip(), "key": key.strip()})
    cleaned = []
    for row in rows:
        key = str(row.get("key") or "").strip()
        project = str(row.get("project") or "default").strip()
        if key:
            cleaned.append({"project": project, "key": key})
    return cleaned


def _usage(project: str):
    day = timezone.localdate()
    row, _ = GeminiProjectUsage.objects.get_or_create(project_number=project, day=day)
    return row


def generate_json(prompt: str, settings) -> tuple[dict | list | None, str]:
    """Call the next project that still has room today. Returns (parsed, project)."""
    keys = load_keys()
    if not keys:
        raise RuntimeError("No Gemini keys are configured on the server.")

    last_error = "No project had free quota left for today."
    ordered = sorted(keys, key=lambda item: _usage(item["project"]).requests)
    for item in ordered:
        usage = _usage(item["project"])
        if usage.requests >= settings.requests_per_project_per_day:
            continue
        if usage.last_error.startswith("quota"):
            continue
        try:
            parsed = _call(item["key"], prompt)
        except RuntimeError as exc:
            message = _redact(str(exc))
            usage.requests += 1
            usage.last_error = message
            if "429" in message or "quota" in message.lower() or "resource_exhausted" in message.lower():
                usage.last_error = "quota reached for today"
            usage.save(update_fields=["requests", "last_error"])
            last_error = message
            continue
        usage.requests += 1
        usage.last_error = ""
        usage.save(update_fields=["requests", "last_error"])
        time.sleep(CALL_GAP_SECONDS)
        return parsed, item["project"]
    raise RuntimeError(last_error)


def record(project: str, *, accepted: int = 0, rejected: int = 0, duplicates: int = 0):
    usage = _usage(project)
    usage.accepted += accepted
    usage.rejected += rejected
    usage.duplicates += duplicates
    usage.save(update_fields=["accepted", "rejected", "duplicates"])


def _call(key: str, prompt: str):
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }
    last = "Gemini did not respond."
    seen = []
    for model in MODELS:
        if not model or model in seen:
            continue
        seen.append(model)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        response = requests.post(
            url,
            headers={"x-goog-api-key": key, "Content-Type": "application/json"},
            json=body,
            timeout=90,
        )
        if response.status_code in (404, 503):
            last = f"Gemini HTTP {response.status_code}: {_redact(response.text)}"
            continue
        if response.status_code != 200:
            raise RuntimeError(f"Gemini HTTP {response.status_code}: {_redact(response.text)}")
        return _parse_json(_response_text(response.json()))
    raise RuntimeError(last)


def _response_text(payload: dict) -> str:
    parts = payload["candidates"][0]["content"]["parts"]
    texts = [str(part.get("text") or "") for part in parts if part.get("text")]
    for text in texts:
        stripped = text.strip()
        if stripped.startswith("{") or stripped.startswith("[") or stripped.startswith("```"):
            return text
    if not texts:
        raise RuntimeError("Gemini returned no text")
    return texts[-1]


def _parse_json(text: str):
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
    return json.loads(raw)


def probe() -> list[str]:
    """Check that each project key can see the model. Does not print the key."""
    lines = []
    for item in load_keys():
        url = "https://generativelanguage.googleapis.com/v1beta/models"
        response = requests.get(
            url,
            headers={"x-goog-api-key": item["key"]},
            params={"pageSize": 5},
            timeout=30,
        )
        if response.status_code != 200:
            lines.append(f"{item['project']}: HTTP {response.status_code} {_redact(response.text)[:120]}")
            continue
        lines.append(f"{item['project']}: reachable ({response.status_code})")
    if not lines:
        lines.append("No keys found.")
    return lines
