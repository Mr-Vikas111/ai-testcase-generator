# Project Guidelines

## Architecture
This repository is an AI-driven API testing system built around a FastAPI backend and a Chrome extension.

Backend structure:
- API layer: `app/api.py`, `app/main.py`, `app/schemas.py`
- Core domain/infrastructure: `app/core/`
- Integrations: `app/integrations/`
- Execution runtime: `app/execution/`
- Patterns: `app/patterns/`
- Entrypoint: `webhook_server.py`

## Build and Test
Use these commands when validating backend changes:
- Start app: `./run_app.sh`
- Entrypoint help: `./run_app.sh --help`
- Syntax compile: `/home/a/techind/projects/nubo-backend/env/bin/python -m compileall app webhook_server.py`

## Agent Delegation
Use the custom agents under `.github/agents/` when the task clearly matches their role.

Delegate to `API Test Orchestrator` when the user wants the full workflow coordinated.
Delegate to `Testcase Generator` when the user asks for test scenarios, API coverage, or QA/security test design.
Delegate to `Test Executor` when the user asks to run the app, validate webhook execution, inspect batches, or verify runtime behavior.
Delegate to `Test Response Analyst` when the user asks to interpret failures, results, or risk after execution.

## Skills
Use the skills under `.github/skills/` for repeatable workflows:
- `api-test-generation` for structured test coverage generation
- `api-test-execution` for real workflow execution checks
- `api-test-reporting` for result triage and QA reporting
- `api-batch-triage` for end-to-end stored batch inspection and risk summary

## Conventions
Keep changes aligned with the current FastAPI package structure.
Prefer focused validation commands after edits.
Preserve the strict JSON contract used by the Ollama integration when modifying test generation.
