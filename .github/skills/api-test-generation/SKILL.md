---
name: api-test-generation
description: "Generate enterprise API test cases from captured requests, cURL, HAR, browser logs, sample responses, or API docs. Use for functional, negative, validation, auth, and security coverage design."
argument-hint: "Provide the API request/response context or describe the endpoint to cover."
user-invocable: true
---

# API Test Generation

## When To Use
- You need enterprise-grade test scenarios for an API endpoint.
- You want functional, negative, auth, validation, boundary, and security coverage.
- You are using captured browser logs or webhook input as the starting point.

## Procedure
1. Read the API input carefully: method, URL, headers, payload, params, response.
2. Identify endpoint purpose, auth model, and validation assumptions.
3. Generate prioritized coverage across:
   - happy path
   - required field validation
   - datatype checks
   - boundary values
   - authorization failures
   - wrong method handling
   - injection and abuse scenarios
4. Keep the output automation-ready and implementation-oriented.
5. Highlight missing context that could affect coverage quality.

## Repo Context
- Prompt implementation lives in [ollama_client.py](../../../app/integrations/ollama_client.py).
- Sanitization rules live in [sanitize.py](../../../app/core/sanitize.py).
- Generated tests are executed later by the runtime workflow.
