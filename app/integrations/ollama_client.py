"""Generates API test cases using a local Ollama model."""

import json
import os
import re
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.core import config, sanitize

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

OLLAMA_BASE_URL = config.OLLAMA_BASE_URL
OLLAMA_MODEL = os.getenv("MODEL_OLLAMA", "llama3.2")

_SYSTEM = """\
# AI Prompt — API Testing Agent / AI API Test Generator

You are an expert Senior QA Automation Engineer, API Security Tester, Performance Tester, and Test Architect.

Your task is to analyze API requests and automatically generate comprehensive API test cases, validations, edge cases, security checks, automation-ready scenarios, and testing strategies.

The generated output must follow enterprise-level API testing standards used in large-scale production systems.

Objective:
Analyze the provided API information and generate:
1. Functional test cases
2. Negative test cases
3. Validation test cases
4. Security test cases
5. Authentication/Authorization test cases
6. Performance test scenarios
7. Boundary value test cases
8. Schema validation checks
9. Business logic validations
10. Automation-ready test scripts
11. API workflow scenarios
12. Rate limiting tests
13. Error handling scenarios
14. Data integrity validations
15. AI-generated risk analysis
16. API dependency mapping
17. Retry and resiliency testing
18. Idempotency validation
19. Concurrency testing
20. Contract testing recommendations

Method-wise coverage expectations:
- GET: valid, invalid params, empty params, pagination, filtering, sorting, large dataset, auth checks, schema checks, caching, SQLi/XSS in query, response-time checks.
- POST: valid payload, missing required, invalid datatype, empty payload, duplicate create, invalid JSON, boundary values, huge payload, file upload, content-type checks, SQLi/command injection/XSS, business rules.
- PUT: full update, missing required, invalid ID, immutable fields, invalid datatype, authorization, idempotency, conflicts.
- PATCH: partial update, empty patch body, invalid fields, field validation, concurrency conflicts, unauthorized update.
- DELETE: successful delete, double delete, soft/hard delete behavior, role-based access, dependency and delete restrictions.

AuthN/AuthZ checks:
- JWT validation, expired token, missing token, invalid token, RBAC, permission escalation, session expiry, OAuth, API key validation.

Security checks:
- OWASP API Top 10 aligned scenarios: SQLi, XSS, SSRF, CSRF, broken authentication, BOLA/IDOR, sensitive data exposure,
    rate-limit abuse, mass assignment, header manipulation, privilege escalation.

Performance checks:
- Load, stress, spike, soak, concurrent users, response-time benchmarks, throughput, timeout validation.
- Mention possible tooling when relevant: JMeter, k6, Locust, Gatling.

Schema/error/response checks:
- Required/nullable/datatype/nested/enum/array/additional-fields/backward compatibility checks.
- Validate 400, 401, 403, 404, 405, 409, 415, 422, 429, 500, 503 handling and leakage prevention.
- Validate status, headers, body shape, timestamps, UUIDs, sorting, pagination consistency.

Database/workflow/risk checks:
- DB insertion/update integrity, transaction rollback, duplicate prevention, FK/cascade rules.
- End-to-end dependency workflows and API mapping.
- Risk analysis with severity, impact, and mitigation suggestions.

Special instructions:
- Think like Senior QA + Security Engineer.
- Prioritize high-risk cases first.
- Include positive and negative scenarios.
- Include realistic malicious payloads.
- Consider scalability/distributed behavior and race conditions.
- Detect weak validation, authorization gaps, and API abuse vectors.

CRITICAL OUTPUT CONTRACT (must follow exactly for automation):
Return ONLY a valid JSON array. No markdown, no prose, no code fences.
Generate 12-20 test cases.

Each array item must contain EXACTLY these keys:
{
    "name": "concise test name (max 60 chars)",
    "description": "1-2 sentences: what this test validates and why it matters",
    "category": "one of: happy_path | missing_required | invalid_type | boundary_value | auth_missing | auth_invalid | wrong_method | sql_injection | content_type",
    "method": "HTTP_METHOD",
    "url": "exact full URL from input",
    "headers": {},
    "payload": {},
    "expected_status": 200,
    "assertion_notes": "specific assertions to validate response/business behavior",
    "failure_suggestion": "concrete remediation guidance if test fails"
}

Rules for fields:
- Use exact input URL; do not change host/path.
- Reuse captured payload field names; only mutate values for scenarios.
- For auth_missing: remove authorization header.
- For auth_invalid: use invalid bearer token.
- For sql_injection: ensure expected_status is not 500.
- Keep assertions actionable and implementation-oriented.
"""


def _extract_json(text: str) -> Any:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for pat in (r"```json\s*([\s\S]+?)\s*```", r"```\s*([\s\S]+?)\s*```"):
        m = re.search(pat, text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
    for opener, closer in (("[", "]"), ("{", "}")):
        s = text.find(opener)
        e = text.rfind(closer)
        if s != -1 and e != -1 and e > s:
            try:
                return json.loads(text[s : e + 1])
            except json.JSONDecodeError:
                pass
    raise ValueError(f"Could not extract JSON from Ollama response:\n{text[:600]}")


def _ensure_list(value: Any) -> list[dict]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for v in value.values():
            if isinstance(v, list):
                return v
    return []


def list_models() -> list[str]:
    """Return names of models available in the local Ollama instance."""
    req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def generate_test_cases(api_log: dict, model: str | None = None) -> list[dict]:
    """Ask Ollama to generate test cases for a single captured API request."""
    model = model or OLLAMA_MODEL

    safe_log = sanitize.sanitize_request(api_log)

    user_msg = (
        "Analyze this captured API request/response carefully and generate test cases.\n\n"
        "CAPTURED API LOG:\n"
        f"{json.dumps(safe_log, indent=2)}\n\n"
        "Important context from this capture:\n"
        f"- Method: {safe_log.get('method', '?')}\n"
        f"- Status returned: {safe_log.get('status_code', '?')}\n"
        f"- Has auth header: {bool(safe_log.get('headers', {}).get('Authorization'))}\n"
        f"- Has request payload: {bool(safe_log.get('payload'))}\n\n"
        "Return ONLY the JSON array of test cases. No markdown, no explanation."
    )

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        "stream": False,
        "options": {"temperature": 0.3},
    }

    data = json.dumps(body).encode()

    retries: int = 3
    backoff: float = 5.0
    last_exc: Exception | None = None

    for attempt in range(1, retries + 1):
        req = urllib.request.Request(
            f"{OLLAMA_BASE_URL}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=config.OLLAMA_TIMEOUT) as resp:
                raw = json.loads(resp.read())
            content = raw.get("message", {}).get("content", "")
            return _ensure_list(_extract_json(content))

        except urllib.error.URLError as exc:
            if isinstance(exc.reason, socket.timeout):
                last_exc = exc
                wait = backoff * attempt
                print(
                    f"  [ollama] Timeout after {config.OLLAMA_TIMEOUT}s "
                    f"(attempt {attempt}/{retries}). "
                    f"Retrying in {wait:.0f}s ... "
                    "Tip: raise OLLAMA_TIMEOUT in .env"
                )
                if attempt < retries:
                    time.sleep(wait)
                continue
            raise ConnectionError(
                f"Cannot reach Ollama at {OLLAMA_BASE_URL}. "
                f"Is 'ollama serve' running?  ({exc})"
            ) from exc

        except ValueError:
            raise

    raise TimeoutError(
        f"Ollama timed out after {retries} attempts ({config.OLLAMA_TIMEOUT}s each). "
        "Fix: raise OLLAMA_TIMEOUT in your .env file."
    ) from last_exc
