# AI Test API

AI Test API is a FastAPI-based webhook service that turns captured browser API traffic into executable API test suites, runs those tests, and produces AI-assisted risk analysis.

It is designed to work with the included Chrome extension in `chrome-extension/`, a local Ollama model, and a target API (for example a Todo API at `http://localhost:8000`).

## What This Project Does

1. Captures API requests and responses from your browser using the Chrome extension.
2. Sends captured data to `POST /webhook`.
3. Validates and sanitizes captured requests.
4. Generates test cases with an LLM (Ollama by default).
5. Executes generated tests against your target API.
6. Runs AI analysis on results and stores final batch output in `storage/`.

## Architecture

Core backend modules:

- API layer: `app/api.py`, `app/main.py`, `app/schemas.py`
- Service/orchestration: `app/services.py`, `app/agents/orchestrator.py`
- LLM integrations: `app/integrations/llm_adapter.py`, `app/integrations/ollama_client.py`
- Runtime execution: `app/execution/test_runner.py`
- Validation/sanitization/storage: `app/core/sanitize.py`, `app/core/store.py`, `app/core/config.py`
- Entrypoint: `webhook_server.py` (called by `run_app.sh`)

Patterns used:

- Facade pattern for webhook business workflow
- Builder pattern for response payload assembly
- Factory pattern for service wiring and adapter selection

## Request Lifecycle

1. Chrome extension captures request/response pairs.
2. Extension posts payload to `POST /webhook`.
3. Server filters and sanitizes requests:
   - Drops invalid URLs, unsupported methods, null status responses, static assets, duplicates.
   - Redacts sensitive headers/tokens/payload values.
4. Batch is persisted and background processing starts.
5. For each API capture:
   - Stage 1: Generate test cases (LLM)
   - Stage 2: Execute test cases (HTTP requests)
6. Stage 3: AI analyst summarizes risk/findings.
7. Results are available via `GET /results/{batch_id}` and saved in `storage/<batch_id>/results.json`.

## Prerequisites

- Python 3.10+ (3.12 recommended)
- Ollama running locally on host (`http://localhost:11434`)

## Environment Configuration

Edit `.env`:

```env
LLM_PROVIDER=ollama
MODEL_OLLAMA=llama3.2
OLLAMA_TIMEOUT=600
OLLAMA_BASE_URL=http://localhost:11434
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4o-mini
```

Notes:

- For local host-run setup, use `OLLAMA_BASE_URL=http://localhost:11434`

## Setup and Run (Host)

### 1) Create virtual environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2) Start Ollama and pull model

```bash
ollama serve
ollama pull llama3.2
```

### 3) Start API server

```bash
./run_app.sh
```

Or with explicit host/port/model:

```bash
./run_app.sh --host 0.0.0.0 --port 5055 --model llama3.2
```

Health check:

```bash
curl -s http://127.0.0.1:5055/health
```

## Chrome Extension Usage

Directory: `chrome-extension/`

1. Open Chrome extensions page (`chrome://extensions`).
2. Enable Developer mode.
3. Click Load unpacked and select `chrome-extension/`.
4. Open target web app.
5. In extension popup:
   - Start capture
   - Perform API actions in browser
   - Stop capture
   - Configure webhook URL as `http://127.0.0.1:5055/webhook` (or your deployed URL)
6. Extension submits captured payload and starts polling `results_url`.

## API Endpoints

### GET /health

Server and model health.

```bash
curl -s http://127.0.0.1:5055/health
```

### POST /webhook

Accepts captured API logs and creates async batch.

```bash
curl -s -X POST http://127.0.0.1:5055/webhook \
  -H 'Content-Type: application/json' \
  -d '{
    "requests": [
      {
        "url": "http://localhost:8000/api/todos",
        "method": "GET",
        "headers": {"Accept": "application/json"},
        "payload": {},
        "response": [{"id": 1, "text": "demo"}],
        "status_code": 200
      }
    ]
  }'
```

Typical response:

```json
{
  "ok": true,
  "batch_id": "a1b2c3d4e5f67890",
  "results_url": "http://127.0.0.1:5055/results/a1b2c3d4e5f67890",
  "total": 1,
  "filter": {
    "original": 1,
    "dropped_no_url": 0,
    "dropped_bad_method": 0,
    "dropped_static_asset": 0,
    "dropped_null_status": 0,
    "dropped_duplicate": 0,
    "kept": 1
  },
  "methods": {
    "GET": 1
  }
}
```

### GET /results/{batch_id}

Fetch live or final results.

```bash
curl -s http://127.0.0.1:5055/results/<batch_id>
```

### GET /batches

List recent batches.

```bash
curl -s 'http://127.0.0.1:5055/batches?limit=50'
```

### GET /admin/cleanup

Remove old batches.

```bash
curl -s 'http://127.0.0.1:5055/admin/cleanup?days=7'
```

## Storage Layout

- `storage/index.json`: batch metadata index
- `storage/<batch_id>/capture.json`: sanitized captured payload
- `storage/<batch_id>/<nn>_<METHOD>_<slug>.json`: per-request snapshot
- `storage/<batch_id>/results.json`: final execution + analysis result

## How Test Execution Works

- The generator creates test cases containing method, URL, headers, payload, expected status, and assertion notes.
- The runner (`app/execution/test_runner.py`) sends HTTP calls exactly to each test case URL.
- Pass/fail is based on status code match (`actual_status == expected_status`).
- Transport issues are reported as errors (ConnectionError, Timeout, RequestError).

## Troubleshooting

### Error: Cannot reach Ollama at http://localhost:11434 ... Connection refused

Cause:

- Ollama service is not running on your machine.

Fix:

- Start Ollama and ensure your model is available.
- Verify `.env` contains `OLLAMA_BASE_URL=http://localhost:11434`.

### Error: HTTP 404 from /api/chat (model not found)

Cause:

- Ollama service is up, but requested model is missing.

Fix:

```bash
ollama pull llama3.2
```

### Error: Connection refused to localhost:8000 during test execution

Cause:

- Target API is not running on port 8000.

Fix:

- Start your target API service and confirm endpoint availability.

## Development and Validation

Run app:

```bash
./run_app.sh
./run_app.sh --help
```

Syntax compile check:

```bash
python -m compileall app webhook_server.py
```

Project-specific environment path example:

```bash
/home/a/techind/projects/nubo-backend/env/bin/python -m compileall app webhook_server.py
```

## Security Notes

- Sensitive headers and payload secrets are redacted before storage/processing.
- Authorization token values are masked.
- Avoid committing real API keys and tokens in `.env`.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
