---
name: api-test-execution
description: "Execute or validate the API test workflow by running the FastAPI app, webhook flow, batch processing, and focused runtime checks. Use for real execution and verification."
argument-hint: "Describe what should be executed or validated."
user-invocable: true
---

# API Test Execution

## When To Use
- You need to run the API testing app or validate a webhook/batch flow.
- You need to confirm generated tests are being processed.
- You need a focused runtime check rather than test design.

## Procedure
1. Start the application using [run_app.sh](../../../run_app.sh) or [webhook_server.py](../../../webhook_server.py).
2. Verify the server with `/health` or the extension test connection flow.
3. Trigger the webhook or use existing stored batches.
4. Inspect runtime behavior, batch status, progress, and result summaries.
5. Report execution failures with exact reproduction context.

## Repo Context
- App entrypoint: [webhook_server.py](../../../webhook_server.py)
- FastAPI app: [main.py](../../../app/main.py)
- Batch store and results persistence: [store.py](../../../app/core/store.py)
- Test execution engine: [test_runner.py](../../../app/execution/test_runner.py)
