"""
Loads system prompts for Python runtime agents from the .github markdown files.

This keeps a single source of truth: the .github/agents/*.agent.md and
.github/skills/*/SKILL.md files define agent persona + approach for both
VS Code Copilot AND the Ollama runtime.

Usage::

    from app.agents.loader import load_agent_prompt

    system = load_agent_prompt(
        agent="testcase-generator",
        skills=["api-test-generation"],
        append=STRICT_JSON_CONTRACT,
    )
"""

from __future__ import annotations

from functools import lru_cache
import re
from pathlib import Path

# Repo root is two levels above app/
# loader.py lives at app/agents/loader.py — parents[2] is the repo root
_REPO_ROOT = Path(__file__).resolve().parents[2]
_AGENTS_DIR = _REPO_ROOT / ".github" / "agents"
_SKILLS_DIR = _REPO_ROOT / ".github" / "skills"

# Use-case composition rules for assembling runtime prompts from .github files.
# Keep these explicit so each runtime step includes only relevant guidance.
_USE_CASE_MAP: dict[str, dict[str, tuple[str, ...]]] = {
    "generate": {
        "agents": ("api-test-orchestrator", "testcase-generator"),
        "skills": ("api-test-generation",),
    },
    "execute": {
        "agents": ("api-test-orchestrator", "test-executor"),
        "skills": ("api-test-execution",),
    },
    "analyse": {
        "agents": ("api-test-orchestrator", "test-response-analyst"),
        "skills": ("api-test-reporting", "api-batch-triage"),
    },
    "full": {
        "agents": (
            "api-test-orchestrator",
            "testcase-generator",
            "test-executor",
            "test-response-analyst",
        ),
        "skills": (
            "api-test-generation",
            "api-test-execution",
            "api-test-reporting",
            "api-batch-triage",
        ),
    },
}


def _strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter (--- ... ---) and return the body."""
    text = text.strip()
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:].lstrip()
    return text


@lru_cache(maxsize=128)
def _load_file(path: Path) -> str:
    """Read a markdown file and strip its frontmatter."""
    try:
        return _strip_frontmatter(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Agent/skill definition not found: {path}\n"
            "Ensure the .github/agents/ and .github/skills/ directories are present."
        )


def load_agent(agent_name: str) -> str:
    """Load body of .github/agents/{agent_name}.agent.md."""
    return _load_file(_AGENTS_DIR / f"{agent_name}.agent.md")


def load_skill(skill_name: str) -> str:
    """Load body of .github/skills/{skill_name}/SKILL.md."""
    return _load_file(_SKILLS_DIR / skill_name / "SKILL.md")


def _normalize_use_case(use_case: str) -> str:
    uc = use_case.strip().lower()
    if uc not in _USE_CASE_MAP:
        supported = ", ".join(sorted(_USE_CASE_MAP))
        raise ValueError(f"Unsupported use_case '{use_case}'. Supported: {supported}")
    return uc


def _compose_prompt(*, agents: tuple[str, ...], skills: tuple[str, ...], append: str = "") -> str:
    parts: list[str] = []

    for agent_name in agents:
        parts.append(f"## Agent: {agent_name}\n\n{load_agent(agent_name)}")

    for skill in skills:
        skill_body = load_skill(skill)
        # Strip Repo Context sections — they link to source files and are
        # only relevant for VS Code Copilot navigation, not Ollama.
        skill_body = re.sub(
            r"## Repo Context\b.*",
            "",
            skill_body,
            flags=re.DOTALL,
        ).rstrip()
        parts.append(f"## Skill: {skill}\n\n{skill_body}")

    if append:
        parts.append(append)

    return "\n\n---\n\n".join(parts)


@lru_cache(maxsize=64)
def _build_use_case_prompt_cached(use_case: str, append: str = "") -> str:
    uc = _normalize_use_case(use_case)
    mapping = _USE_CASE_MAP[uc]
    return _compose_prompt(
        agents=mapping["agents"],
        skills=mapping["skills"],
        append=append,
    )


def load_use_case_prompt(*, use_case: str, append: str = "") -> str:
    """
    Build a prompt by use case, automatically including all relevant agents/skills.

    Supported use cases:
      - generate
      - execute
      - analyse
      - full
    """
    return _build_use_case_prompt_cached(use_case, append)


def load_agent_prompt(*, agent: str, skills: list[str] | None = None, append: str = "") -> str:
    """
    Build a complete Ollama system prompt from .github definition files.

    Combines:
      1. Agent identity from .github/agents/{agent}.agent.md
      2. Skill procedure(s) from .github/skills/{skill}/SKILL.md
      3. An optional strict output contract appended at the end

    Args:
        agent:  agent file stem, e.g. "testcase-generator"
        skills: list of skill names to include, e.g. ["api-test-generation"]
        append: additional instructions appended verbatim (e.g. JSON contract)

    Returns:
        Assembled system prompt string.
    """
    # Backward-compatible single-agent mode.
    return _compose_prompt(
        agents=(agent,),
        skills=tuple(skills or []),
        append=append,
    )
