---
title: Serving Pipelines
description: Run pipelines as fast HTTP services with async serving by default and optional memory-only execution.
---

# Serving Pipelines

ZenML Serving exposes a pipeline as a FastAPI service. In serving, execution uses a Realtime runtime with async server updates by default for low latency. You can optionally run memory-only for maximum speed.

## Why Serving vs. Orchestrators

- Performance: Async serving with in-process caching for low latency.
- Simplicity: Invoke your pipeline over HTTP; get results or stream progress.
- Control: Single, typed `Capture` config to tune observability or enable memory-only.

Use orchestrators for scheduled, reproducible workflows. Use Serving for request/response inference.

## Quickstart

Prerequisites

- A deployed pipeline; note its deployment UUID as `ZENML_PIPELINE_DEPLOYMENT_ID`.

Start the service

```bash
export ZENML_PIPELINE_DEPLOYMENT_ID="<deployment-uuid>"
export ZENML_SERVICE_HOST=0.0.0.0
export ZENML_SERVICE_PORT=8001
python -m zenml.deployers.serving.app
```

Invoke (sync)

```bash
curl -s -X POST "http://localhost:8001/invoke" \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"your_param": "value"}}'
```

## Capture (typed-only)

Configure capture at the pipeline decorator using a single, typed `Capture`:

```python
from zenml import pipeline
from zenml.capture.config import Capture

@pipeline(capture=Capture())  # serving async by default
def serve_pipeline(...):
    ...

@pipeline(capture=Capture(memory_only=True))  # serving only
def max_speed_pipeline(...):
    ...
```

Options (observability only; do not affect dataflow):
- `code`: include code/source/docstrings in metadata (default True)
- `logs`: persist step logs (default True)
- `metadata`: publish run/step metadata (default True)
- `visualizations`: persist visualizations (default True)
- `metrics`: emit runtime metrics (default True)

Notes
- Serving is async by default; there is no `flush_on_step_end` knob.
- `memory_only=True` is ignored outside serving with a warning.

## Request Parameters

Request JSON under `parameters` is merged into the effective step config in serving. Logged keys indicate which parameters were applied.

## Execution Modes

- Sync: `POST /invoke` waits for completion; returns results or error.
- Async: `POST /invoke?mode=async` returns a `job_id`; poll `GET /jobs/{job_id}`.
- Streaming: `GET /stream/{job_id}` (SSE) or `WebSocket /stream` to stream progress.

Async example

```bash
JOB_ID=$(curl -s -X POST "http://localhost:8001/invoke?mode=async" \
  -H "Content-Type: application/json" -d '{"parameters":{}}' | jq -r .job_id)
curl -s "http://localhost:8001/jobs/$JOB_ID"
```

SSE

```bash
curl -N -H "Accept: text/event-stream" "http://localhost:8001/stream/$JOB_ID"
```

## Operations

- `/health`: Service health and uptime.
- `/info`: Pipeline name, steps, parameter schema, deployment info.
- `/metrics`: Execution statistics (queue depth, cache hit rate, latencies when metrics enabled).
- `/status`: Service configuration snapshot.
- `/invoke`: Execute (sync/async) with optional parameters.
- `/jobs`, `/jobs/{id}`, `/jobs/{id}/cancel`: Manage async jobs.
- `/stream/{id}`: Server‑Sent Events stream; `WebSocket /stream` for bidirectional.

## Troubleshooting

- Missing deployment ID: set `ZENML_PIPELINE_DEPLOYMENT_ID`.
- Slow responses: ensure you are in serving (async by default) or consider `Capture(memory_only=True)` for prototypes.
- Multi-worker/safety: Serving isolates request state; taps are cleared per request.

## See Also

- Capture & Runtimes (advanced): serving defaults, toggles, memory-only behavior.
- Realtime Tuning: cache TTL/size, error reporting, and circuit breaker knobs.
