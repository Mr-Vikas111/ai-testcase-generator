---
name: api-batch-triage
description: "Inspect stored API batch results end to end, summarize execution health, classify risks, and recommend next actions. Use for batch triage, failed run analysis, and QA status reporting."
argument-hint: "Provide a batch ID, results payload, or describe the batch issue to triage."
user-invocable: true
---

# API Batch Triage

## When To Use
- You have a stored batch ID and need an end-to-end summary.
- A webhook run completed with mixed pass/fail/error results.
- You need to combine execution facts with QA and risk analysis.
- You want a concise status report for a generated API testing batch.

## Procedure
1. Identify the batch source:
   - stored batch ID
   - `/results/{batch_id}` payload
   - copied result summary
2. Read the batch summary, progress, grouped request results, and any per-test failures.
3. Separate:
   - passed validations
   - assertion failures
   - environment/runtime errors
   - likely flaky or dependency-driven failures
4. Classify issues by severity and business impact.
5. Recommend the next action:
   - regenerate tests
   - rerun execution
   - fix backend behavior
   - inspect auth, schema, validation, or rate limiting logic
6. Produce a compact triage summary suitable for QA/SDET review.

## Output Template
- Batch overview
- Execution health
- High-severity findings
- Likely root causes
- Recommended next actions
- Residual risks

## Repo Context
- Stored batch results live under `storage/{batch_id}/results.json`
- Batch persistence: [store.py](../../../app/core/store.py)
- API result routes: [api.py](../../../app/api.py)
- Runtime orchestration: [services.py](../../../app/services.py)
- Execution engine: [test_runner.py](../../../app/execution/test_runner.py)
