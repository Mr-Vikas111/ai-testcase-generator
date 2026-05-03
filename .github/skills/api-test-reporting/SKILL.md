---
name: api-test-reporting
description: "Analyze API test execution results, summarize risks, explain failures, and recommend fixes. Use for QA reporting, triage, and response interpretation."
argument-hint: "Provide result data, batch output, or failing test details."
user-invocable: true
---

# API Test Reporting

## When To Use
- You have test results and need interpretation.
- You want failure triage and risk-based prioritization.
- You need recommendations after execution.

## Procedure
1. Read the batch summary, grouped results, and individual failures.
2. Distinguish assertion failures from runtime or environment errors.
3. Classify findings by severity, likely root cause, and affected behavior.
4. Recommend targeted fixes and follow-up checks.
5. Call out residual risk and missing coverage.

## Repo Context
- Results API and workflow: [api.py](../../../app/api.py)
- Runtime orchestration: [services.py](../../../app/services.py)
- Stored batch results: [store.py](../../../app/core/store.py)
