"""Configuration loader. Reads from .env file (or environment variables)."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

# Timeout (seconds) for a single LLM request (Ollama or OpenAI).
OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "600"))

# LLM provider selection: 'ollama' (default) or 'openai'.
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")

# OpenAI settings (only required when LLM_PROVIDER=openai).
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
