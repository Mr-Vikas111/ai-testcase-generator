# API Test Workflow Orchestrator

This file documents the intended multi-agent workflow for this repository.

## Agents
- `API Test Orchestrator`
- `Testcase Generator`
- `Test Executor`
- `Test Response Analyst`

## End-to-End Flow
1. `API Test Orchestrator` receives the user goal and identifies the current stage.
2. `Testcase Generator` produces high-quality API test scenarios from captured input or endpoint context.
3. `Test Executor` runs the narrowest viable execution path, such as starting the app, validating `/health`, invoking webhook processing, or checking stored batches.
4. `Test Response Analyst` interprets pass/fail/error output, groups findings by severity, and recommends fixes.
5. `API Test Orchestrator` consolidates the result and presents the next action or final outcome.

## Delegation Rules
- Use `Testcase Generator` for prompt-driven scenario creation and coverage expansion.
- Use `Test Executor` for any runnable verification, webhook flow, or batch/result checks.
- Use `Test Response Analyst` after execution when evidence exists to interpret.

## Guardrails
- Do not skip execution if a focused validation exists.
- Do not analyze results without actual runtime evidence when execution is possible.
- Do not generate speculative endpoints or unsupported assumptions.

## Repo Mapping
- Prompt generation: [ollama_client.py](../app/integrations/ollama_client.py)
- Execution runtime: [test_runner.py](../app/execution/test_runner.py)
- Results storage: [store.py](../app/core/store.py)
- API routes: [api.py](../app/api.py)
