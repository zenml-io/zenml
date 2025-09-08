# ZenML Pipeline Serving Examples

This directory contains examples that run pipelines as HTTP services using ZenML Serving.

Highlights

- Async serving by default for low latency
- Optional memory-only execution via `Capture(memory_only=True)`
- Request parameter merging and streaming support

## Files

1. `weather_pipeline.py` – simple weather analysis
2. `chat_agent_pipeline.py` – conversational agent with streaming
3. `test_serving.py` – basic endpoint checks

## Serving Modes (by context)

- Batch (outside serving): blocking publishes; standard persistence
- Serving (default): async publishes with in‑process cache
- Memory-only (serving only): in‑process handoff; no DB/artifacts

## Quick Start: Weather Agent

1) Create and deploy the pipeline

```bash
python weather_pipeline.py
```

2) Start the serving service

```bash
export ZENML_PIPELINE_DEPLOYMENT_ID=<deployment-id>
python -m zenml.deployers.serving.app
```

3) Invoke

```bash
curl -X POST "http://localhost:8000/invoke" \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"city": "Paris"}}'
```

Service defaults

- Host: `http://localhost:8000`
- Serving: async by default

## Configuration

```bash
export ZENML_PIPELINE_DEPLOYMENT_ID=<deployment-id>
python -m zenml.deployers.serving.app
```

To enable memory-only mode, set it in code:

```python
from zenml import pipeline
from zenml.capture.config import Capture

@pipeline(capture=Capture(memory_only=True))
def serve_max_speed(...):
    ...
```

## Execution Flow (serving)

Request → Parameter merge → StepRunner → Response

- Parameters under `parameters` are merged into step config.
- Serving is async; background updates do not block the response.

## API Reference

Core endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/invoke` | POST | Execute pipeline (sync or async) |
| `/health` | GET | Service health |
| `/info` | GET | Pipeline schema & deployment info |
| `/metrics` | GET | Runtime metrics (if enabled) |
| `/jobs`, `/jobs/{id}` | GET | Manage async jobs |
| `/stream/{id}` | GET | Server‑Sent Events stream |

Request format

```json
{
  "parameters": {
    "city": "string"
  }
}
```

## Troubleshooting

- Missing deployment ID: set `ZENML_PIPELINE_DEPLOYMENT_ID`.
- Slow responses: serving is async by default; for prototypes consider `Capture(memory_only=True)`.
- Monitor: use `/metrics` for queue depth, cache hit rate, and latencies.

## Docker

```dockerfile
FROM python:3.11-slim
RUN pip install zenml
ENV ZENML_SERVICE_HOST=0.0.0.0
ENV ZENML_SERVICE_PORT=8000
CMD ["python", "-m", "zenml.deployers.serving.app"]
```

## Kubernetes (snippet)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: zenml-serving
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: serving
        image: zenml-serving:latest
        env:
        - name: ZENML_PIPELINE_DEPLOYMENT_ID
          value: "your-deployment-id"
        ports:
        - containerPort: 8000
```

