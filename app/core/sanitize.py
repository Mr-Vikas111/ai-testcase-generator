"""
sanitize.py  —  Data-layer validation and sanitization for captured API requests.

Applied at storage level (before writing to disk) and before sending to Ollama.

Two responsibilities:
  1. filter_requests()  — drop invalid / duplicate / low-value entries
  2. sanitize_request() — redact credentials so they are never stored in plain text

Filters applied (in order):
  a. Must have a non-empty URL starting with http
  b. Method must be one of GET POST PUT PATCH DELETE
  c. status_code must not be null (incomplete captures have nothing to test)
  d. Deduplicate by (METHOD, path-without-query) — keep first occurrence

Redactions applied to every saved/processed request:
  - Header values matching sensitive key names  → "<REDACTED>"
  - Bearer tokens in Authorization              → "Bearer <TOKEN>"
  - Payload keys matching password/secret patterns → "<REDACTED>"
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

# ── Constants ─────────────────────────────────────────────────────────────────

VALID_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}

# Static asset extensions that are never API endpoints
_STATIC_EXTENSIONS_RE = re.compile(
    r"\.(js|jsx|ts|tsx|css|html|htm|ico|png|jpg|jpeg|gif|svg|webp|woff|woff2|ttf|eot|map|gz|zip)$",
    re.IGNORECASE,
)

# Header names whose values should never be stored verbatim
_SENSITIVE_HEADERS: frozenset[str] = frozenset({
    "authorization",
    "x-api-key",
    "x-auth-token",
    "x-access-token",
    "cookie",
    "set-cookie",
    "proxy-authorization",
})

# Payload keys whose values should never be stored verbatim
_SENSITIVE_PAYLOAD_KEYS_RE = re.compile(
    r"(password|passwd|secret|token|api_key|apikey|auth|credential|private_key)",
    re.IGNORECASE,
)


# ── Validation errors ─────────────────────────────────────────────────────────


class ValidationError(Exception):
    pass


# ── Public API ────────────────────────────────────────────────────────────────


def filter_requests(
    requests_list: list[dict],
) -> tuple[list[dict], dict]:
    """
    Validate, deduplicate, and sanitize a list of captured requests.

    Returns:
        (clean_list, report)
        clean_list — filtered + sanitized requests, ready for storage/Ollama
        report     — counts of what was dropped and why, for server response
    """
    if not isinstance(requests_list, list):
        raise ValidationError("'requests' must be a list")

    report: dict[str, Any] = {
        "original": len(requests_list),
        "dropped_no_url": 0,
        "dropped_bad_method": 0,
        "dropped_static_asset": 0,
        "dropped_null_status": 0,
        "dropped_duplicate": 0,
        "kept": 0,
    }

    seen: set[tuple[str, str]] = set()  # (METHOD, normalised-path)
    clean: list[dict] = []

    for req in requests_list:
        # Guard: skip any non-dict entries (malformed captures)
        if not isinstance(req, dict):
            report["dropped_no_url"] += 1
            continue

        url = (req.get("url") or "").strip()
        method = (req.get("method") or "").upper().strip()
        status = req.get("status_code")

        # a. URL must be present and absolute
        if not url or not url.startswith("http"):
            report["dropped_no_url"] += 1
            continue

        # b. Method must be a trackable verb
        if method not in VALID_METHODS:
            report["dropped_bad_method"] += 1
            continue

        # c. Drop static asset URLs (js, css, images, fonts…)
        try:
            path_only = urlparse(url).path
        except Exception:
            path_only = url
        if _STATIC_EXTENSIONS_RE.search(path_only):
            report["dropped_static_asset"] += 1
            continue

        # d. Require a completed response (status_code not null)
        if status is None:
            report["dropped_null_status"] += 1
            continue

        # e. Deduplicate by (method, path without query string)
        key = (method, path_only)
        if key in seen:
            report["dropped_duplicate"] += 1
            continue
        seen.add(key)

        # Sanitize before storing
        clean.append(sanitize_request(req))
        report["kept"] += 1

    return clean, report


def sanitize_request(req: dict) -> dict:
    """
    Return a copy of *req* with sensitive values redacted.

    - Authorization: Bearer <anything>  →  Authorization: Bearer <TOKEN>
    - Other sensitive header names       →  <REDACTED>
    - Sensitive payload key values       →  <REDACTED>
    """
    result = dict(req)

    # Headers
    raw_headers = req.get("headers") or {}
    if isinstance(raw_headers, dict):
        clean_headers: dict[str, str] = {}
        for k, v in raw_headers.items():
            key_lower = k.lower()
            if key_lower == "authorization":
                # Keep scheme, redact token
                val_str = str(v)
                if val_str.lower().startswith("bearer "):
                    clean_headers[k] = "Bearer <TOKEN>"
                else:
                    clean_headers[k] = "<REDACTED>"
            elif key_lower in _SENSITIVE_HEADERS:
                clean_headers[k] = "<REDACTED>"
            else:
                clean_headers[k] = v
        result["headers"] = clean_headers

    # Payload
    raw_payload = req.get("payload")
    if isinstance(raw_payload, dict):
        result["payload"] = _redact_dict(raw_payload)

    return result


# ── Private helpers ───────────────────────────────────────────────────────────


def _redact_dict(d: dict, _depth: int = 0) -> dict:
    """Recursively redact sensitive keys in a payload dict (max 5 levels deep)."""
    if _depth > 5:
        return d
    out: dict = {}
    for k, v in d.items():
        if _SENSITIVE_PAYLOAD_KEYS_RE.search(str(k)):
            out[k] = "<REDACTED>"
        elif isinstance(v, dict):
            out[k] = _redact_dict(v, _depth + 1)
        elif isinstance(v, list):
            out[k] = [
                _redact_dict(item, _depth + 1) if isinstance(item, dict) else item
                for item in v
            ]
        else:
            out[k] = v
    return out
