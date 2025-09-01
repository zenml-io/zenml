---
title: Serving Pipelines
description: Low‑latency pipeline execution over HTTP/WebSocket with optional tracking and streaming.
---

# Serving Pipelines

ZenML Serving runs pipelines in a low‑latency FastAPI service, without orchestrators or artifact stores. It’s ideal for real‑time inference, agents, and interactive workflows.

## Why Serving vs. Orchestrators

- Performance: Direct in‑process execution (no container builds, no remote schedulers).
- Simplicity: Call your pipeline via HTTP/WebSocket; get results or stream progress.
- Observability: Optional run/step tracking with capture policies (privacy‑aware).

Use orchestrators for scheduled, long‑running, reproducible workflows; use Serving for real‑time request/response.

## How It Works

- DirectExecutionEngine: Executes the compiled deployment graph directly, step‑by‑step.
- ServingExecutionManager: Enforces concurrency/queue limits and timeouts.
- JobRegistry: Tracks async jobs and cancellation.
- StreamManager: Streams step/pipeline events (SSE/WebSockets) with heartbeats.
- Tracking (optional): Records runs, steps, previews, and artifacts according to capture policies.

Startup loads the target deployment (via `ZENML_PIPELINE_DEPLOYMENT_ID`), wires job→stream cleanup, and starts background maintenance tasks. Shutdown stops managers cleanly.

## Quickstart

Prerequisites

- A deployed pipeline; note its deployment UUID as `ZENML_PIPELINE_DEPLOYMENT_ID`.
- Python env with dev deps (as per CONTRIBUTING).

Start the service

```bash
export ZENML_PIPELINE_DEPLOYMENT_ID="<deployment-uuid>"
export ZENML_SERVICE_HOST=0.0.0.0
export ZENML_SERVICE_PORT=8001
uvicorn zenml.serving.app:app --host "$ZENML_SERVICE_HOST" --port "$ZENML_SERVICE_PORT"
```

Synchronous invocation

```bash
curl -s -X POST "http://localhost:8001/invoke" \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"your_param": "value"}}'
```

## Execution Modes

- Sync: `POST /invoke` waits for completion; returns results or error.
- Async: `POST /invoke?mode=async` returns a `job_id`; poll `GET /jobs/{job_id}`.
- Streaming: `GET /stream/{job_id}` (SSE) or `WebSocket /stream` to receive progress and completion events in real time.

Async example

```bash
# Submit
JOB_ID=$(curl -s -X POST "http://localhost:8001/invoke?mode=async" -H "Content-Type: application/json" -d '{"parameters":{}}' | jq -r .job_id)

# Poll
curl -s "http://localhost:8001/jobs/$JOB_ID"
```

SSE example

```bash
curl -N -H "Accept: text/event-stream" "http://localhost:8001/stream/$JOB_ID"
```

## Operations

- `/health`: Service health and uptime.
- `/info`: Pipeline name, steps, parameter schema, deployment info.
- `/metrics`: Execution statistics (counts, averages).
- `/status`: Service configuration snapshot.
- `/invoke`: Execute (sync/async) with optional `capture_override`.
- `/jobs`, `/jobs/{id}`, `/jobs/{id}/cancel`: Manage async jobs.
- `/stream/{id}`: Server‑Sent Events stream for a job; `WebSocket /stream` for bidirectional.

Concurrency and backpressure

- Limits concurrent executions; queues up to a configured size; rejects overload with HTTP 429 + `Retry-After`.
- Timeouts apply per request; long steps should be increased or moved to orchestrators.

Key environment variables

- `ZENML_PIPELINE_DEPLOYMENT_ID`: Deployment UUID (required).
- `ZENML_SERVING_MAX_CONCURRENCY` (default: CPU*5).
- `ZENML_SERVING_MAX_QUEUE_SIZE` (default: 100).
- `ZENML_SERVING_REQUEST_TIMEOUT` (default: 300s).
- `ZENML_SERVICE_HOST` (default: `0.0.0.0`), `ZENML_SERVICE_PORT` (default: `8001`), `ZENML_LOG_LEVEL`.
- Disable run creation (ops safeguard): `ZENML_SERVING_CREATE_RUNS=false`.

## Capture Policies (Observability & Privacy)

Capture policies control what gets recorded per invocation, balancing observability with privacy and cost.

- Modes: `full`, `sampled`, `errors_only`, `metadata`, `none`.
- Configuration locations:
  - Pipeline‑level: `@pipeline(settings={"serving_capture": {...}})`.
  - Step‑level: `@step(settings={"serving_capture": {...}})` (overrides pipeline).
  - Type annotations: `Capture` for per‑value hints (used if settings don’t specify per‑value policies).
- Precedence:
  - Global: `Step.mode > Request.mode > Pipeline.mode > Default`.
  - Per‑value: `Step > Pipeline > Annotation > Derived from global`.
- Request overrides:

```json
POST /invoke
{
  "parameters": {"text": "Hello"},
  "capture_override": {"mode": "metadata"}
}
```

Artifacts are derived from mode (e.g., `full` → persist outputs). Sensitive fields are redacted by default; large payloads are truncated. Deterministic sampling ensures consistent behavior within an invocation.

See the detailed guide: [Pipeline Serving Capture Policies](./capture-policies.md).

## Testing & Local Dev

- Exercise endpoints locally with curl or HTTP clients.
- In tests, override FastAPI dependencies to bypass deployment loading and inject test doubles.

## Troubleshooting

- Missing deployment ID: set `ZENML_PIPELINE_DEPLOYMENT_ID`.
- Overload (429): increase `ZENML_SERVING_MAX_CONCURRENCY`/`ZENML_SERVING_MAX_QUEUE_SIZE` or reduce load.
- Timeouts: adjust `ZENML_SERVING_REQUEST_TIMEOUT` or move long runs to orchestrators.
- Streaming disconnects: SSE heartbeats are included; reconnect and resume polling `/jobs/{id}`.
