"""LLM provider adapters — Ollama and OpenAI behind a common interface.

Adapter pattern: agents call LLMAdapter.chat() without knowing the backend.
Select the provider via the LLM_PROVIDER env var (default: ollama) or by
passing ``provider=`` to AdapterFactory.create().

Supported providers
-------------------
* ``ollama``  — local Ollama server (no API key required)
* ``openai``  — OpenAI chat completions API (requires OPENAI_API_KEY)
"""

from __future__ import annotations

import abc
import json
import logging
import os
import socket
import time
import urllib.error
import urllib.request
from typing import Any

from app.core import config

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class LLMAdapter(abc.ABC):
    """Common interface for all LLM provider adapters."""

    @abc.abstractmethod
    def chat(
        self,
        system: str,
        user: str,
        model: str,
        temperature: float = 0.3,
    ) -> str:
        """Send a chat request and return the response content string."""


# ---------------------------------------------------------------------------
# Ollama adapter
# ---------------------------------------------------------------------------


class OllamaAdapter(LLMAdapter):
    """Adapter for a locally running Ollama inference server."""

    _RETRIES: int = 3
    _BACKOFF: float = 5.0

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = (base_url or config.OLLAMA_BASE_URL).rstrip("/")

    def chat(
        self,
        system: str,
        user: str,
        model: str,
        temperature: float = 0.3,
    ) -> str:
        log.debug("OllamaAdapter.chat — model=%s temperature=%s user_chars=%d", model, temperature, len(user))
        body: bytes = json.dumps(
            {
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
                "options": {"temperature": temperature},
            }
        ).encode()

        last_exc: Exception | None = None

        for attempt in range(1, self._RETRIES + 1):
            req = urllib.request.Request(
                f"{self._base_url}/api/chat",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=config.OLLAMA_TIMEOUT) as resp:
                    raw: dict[str, Any] = json.loads(resp.read())
                content = raw.get("message", {}).get("content", "")
                log.debug("OllamaAdapter.chat — response received, chars=%d", len(content))
                return content
            except urllib.error.URLError as exc:
                if isinstance(exc.reason, socket.timeout):
                    last_exc = exc
                    wait = self._BACKOFF * attempt
                    log.warning(
                        "OllamaAdapter.chat — timeout on attempt %d/%d, retrying in %.0fs",
                        attempt, self._RETRIES, wait,
                    )
                    if attempt < self._RETRIES:
                        time.sleep(wait)
                    continue
                log.error("OllamaAdapter.chat — connection error: %s", exc)
                raise ConnectionError(
                    f"Cannot reach Ollama at {self._base_url}: {exc}"
                ) from exc

        log.error(
            "OllamaAdapter.chat — timed out after %d attempts (%ds each)",
            self._RETRIES, config.OLLAMA_TIMEOUT,
        )
        raise TimeoutError(
            f"Ollama timed out after {self._RETRIES} attempts ({config.OLLAMA_TIMEOUT}s each). "
            "Tip: raise OLLAMA_TIMEOUT in .env"
        ) from last_exc


# ---------------------------------------------------------------------------
# OpenAI adapter
# ---------------------------------------------------------------------------


class OpenAIAdapter(LLMAdapter):
    """Adapter for the OpenAI chat completions REST API (no SDK dependency)."""

    _BASE_URL: str = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str | None = None) -> None:
        resolved_key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not resolved_key:
            raise ValueError(
                "OpenAIAdapter requires OPENAI_API_KEY to be set "
                "(env var or api_key= argument)."
            )
        self._api_key = resolved_key
        log.info("OpenAIAdapter initialised")

    def chat(
        self,
        system: str,
        user: str,
        model: str,
        temperature: float = 0.3,
    ) -> str:
        log.debug("OpenAIAdapter.chat — model=%s temperature=%s user_chars=%d", model, temperature, len(user))
        body: bytes = json.dumps(
            {
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": temperature,
            }
        ).encode()

        req = urllib.request.Request(
            self._BASE_URL,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=config.OLLAMA_TIMEOUT) as resp:
                raw: dict[str, Any] = json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode(errors="replace")
            log.error("OpenAIAdapter.chat — HTTP %d: %s", exc.code, body_text[:200])
            raise RuntimeError(
                f"OpenAI API returned HTTP {exc.code}: {body_text}"
            ) from exc
        except urllib.error.URLError as exc:
            log.error("OpenAIAdapter.chat — connection error: %s", exc)
            raise ConnectionError(f"Cannot reach OpenAI API: {exc}") from exc

        choices = raw.get("choices", [])
        if not choices:
            log.warning("OpenAIAdapter.chat — response had no choices")
            return ""
        content = choices[0].get("message", {}).get("content", "")
        log.debug("OpenAIAdapter.chat — response received, chars=%d", len(content))
        return content


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class AdapterFactory:
    """Creates the correct LLMAdapter for the requested provider.

    Usage::

        adapter = AdapterFactory.create()              # defaults to Ollama
        adapter = AdapterFactory.create("openai")      # OpenAI
        adapter = AdapterFactory.create("openai", api_key="sk-...")
    """

    _PROVIDERS: dict[str, type[LLMAdapter]] = {
        "ollama": OllamaAdapter,
        "openai": OpenAIAdapter,
    }

    @classmethod
    def create(
        cls,
        provider: str | None = None,
        **kwargs: Any,
    ) -> LLMAdapter:
        """Return an LLMAdapter instance. Defaults to ``ollama`` if not specified."""
        name = (provider or os.getenv("LLM_PROVIDER", "ollama")).strip().lower()
        klass = cls._PROVIDERS.get(name)
        if klass is None:
            supported = ", ".join(f"'{p}'" for p in cls._PROVIDERS)
            raise ValueError(
                f"Unknown LLM provider: {name!r}. Supported: {supported}."
            )
        log.info("AdapterFactory — creating adapter for provider=%r", name)
        return klass(**kwargs)
