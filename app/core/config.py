"""Configuration loader. Reads from .env file (or environment variables)."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

# Timeout (seconds) for a single LLM request (Ollama or OpenAI).
OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "600"))

# Ollama base URL. In Docker Compose, set this to http://ollama:11434.
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")

# LLM provider selection: 'ollama' (default) or 'openai'.
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")

# OpenAI settings (only required when LLM_PROVIDER=openai).
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
