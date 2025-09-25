---
title: Serving Pipelines
description: Millisecond-class pipeline execution over HTTP with intelligent run-only optimization and streaming.
---

# Serving Pipelines

ZenML Serving runs pipelines as ultra-fast FastAPI services, achieving millisecond-class latency through intelligent run-only execution. Perfect for real-time inference, AI agents, and interactive workflows.

## Why Serving vs. Orchestrators

- **Performance**: Millisecond-class latency with run-only execution (no DB/FS writes in fast mode)
- **Simplicity**: Call your pipeline via HTTP; get results or stream progress 
- **Intelligence**: Automatically switches between tracking and run-only modes based on capture settings
- **Flexibility**: Optional run/step tracking with fine-grained capture policies

Use orchestrators for scheduled, long-running, reproducible workflows; use Serving for real-time request/response.

## How It Works

**Run-Only Architecture** (for millisecond latency):
- **ServingOverrides**: Per-request parameter injection using ContextVar isolation
- **ServingBuffer**: In-memory step output handoff with no persistence
- **Effective Config**: Runtime configuration merging without model mutations  
- **Skip I/O**: Bypasses all database writes and filesystem operations
- **Input Injection**: Upstream step outputs automatically injected as parameters

**Full Tracking Mode** (when capture enabled):
- Traditional ZenML tracking with runs, steps, artifacts, and metadata
- Orchestrator-based execution with full observability

The service automatically chooses the optimal execution mode based on your capture settings.

## Quickstart

Prerequisites

- A deployed pipeline; note its deployment UUID as `ZENML_PIPELINE_DEPLOYMENT_ID`.
- Python env with dev deps (as per CONTRIBUTING).

Start the service

```bash
export ZENML_PIPELINE_DEPLOYMENT_ID="<deployment-uuid>"
export ZENML_SERVICE_HOST=0.0.0.0
export ZENML_SERVICE_PORT=8001
python -m zenml.deployers.server.app
```

Synchronous invocation

```bash
curl -s -X POST "http://localhost:8001/invoke" \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"your_param": "value"}}'
```

## Performance Modes

ZenML Serving automatically chooses the optimal execution mode:

### Run-Only Mode (Millisecond Latency)

Activated when `capture="none"` or no capture settings specified:

```python
@pipeline(settings={"capture": "none"})
def fast_pipeline(x: int) -> int:
    return x * 2
```

**Optimizations**:
- ✅ Zero database writes
- ✅ Zero filesystem operations  
- ✅ In-memory step output handoff
- ✅ Per-request parameter injection
- ✅ Effective configuration merging
- ✅ Multi-worker safe (ContextVar isolation)

**Use for**: Real-time inference, AI agents, interactive demos

### Full Tracking Mode

Activated when capture settings specify tracking:

```python
@pipeline(settings={"capture": "full"})  
def tracked_pipeline(x: int) -> int:
    return x * 2
```

**Features**:
- Complete run/step tracking
- Artifact persistence  
- Metadata collection
- Dashboard integration

**Use for**: Experimentation, debugging, audit trails

## Execution Modes

- **Sync**: `POST /invoke` waits for completion; returns results or error.
- **Async**: `POST /invoke?mode=async` returns a `job_id`; poll `GET /jobs/{job_id}`.
- **Streaming**: `GET /stream/{job_id}` (SSE) or `WebSocket /stream` to receive progress and completion events in real time.

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
- `/invoke`: Execute (sync/async) with optional parameter overrides.
- `/jobs`, `/jobs/{id}`, `/jobs/{id}/cancel`: Manage async jobs.
- `/stream/{id}`: Server‑Sent Events stream for a job; `WebSocket /stream` for bidirectional.

## Configuration

Key environment variables

- `ZENML_PIPELINE_DEPLOYMENT_ID`: Deployment UUID (required).
- `ZENML_DEPLOYMENT_CAPTURE_DEFAULT`: Default capture mode (`none` for run-only, `full` for tracking).
- `ZENML_SERVICE_HOST` (default: `0.0.0.0`), `ZENML_SERVICE_PORT` (default: `8001`).
- `ZENML_LOG_LEVEL`: Logging verbosity.

## Capture Policies

Control what gets tracked per invocation:

- **`none`**: Run-only mode, millisecond latency, no persistence
- **`metadata`**: Track runs/steps, no payload data  
- **`full`**: Complete tracking with artifacts and metadata
- **`sampled`**: Probabilistic tracking for cost control
- **`errors_only`**: Track only failed executions

Configuration locations:
- **Pipeline-level**: `@pipeline(settings={"capture": "none"})`
- **Request-level**: `{"capture_override": {"mode": "full"}}`
- **Environment**: `ZENML_DEPLOYMENT_CAPTURE_DEFAULT=none`

Precedence: Request > Pipeline > Environment > Default

## Advanced Features

### Input/Output Contracts

Pipelines automatically expose their signature:

```python
@pipeline
def my_pipeline(city: str, temperature: float) -> str:
    return process_weather(city, temperature)

# Automatic parameter schema:
# {"city": {"type": "str", "required": true},
#  "temperature": {"type": "float", "required": true}}
```

### Multi-Step Pipelines  

Step outputs automatically injected as inputs:

```python
@step
def fetch_data(city: str) -> dict:
    return {"weather": "sunny", "temp": 25}

@step  
def analyze_data(weather_data: dict) -> str:
    return f"Analysis: {weather_data}"

@pipeline
def weather_pipeline(city: str) -> str:
    data = fetch_data(city)
    return analyze_data(data)  # weather_data auto-injected
```

### Response Building

Only declared pipeline outputs returned:

```python
@pipeline
def multi_output_pipeline(x: int) -> tuple[int, str]:
    return x * 2, f"Result: {x}"

# Response: {"outputs": {"output_0": 4, "output_1": "Result: 2"}}
```

## Testing & Local Dev

Exercise endpoints locally:

```bash
# Health check
curl http://localhost:8001/health

# Pipeline info  
curl http://localhost:8001/info

# Execute with parameters
curl -X POST http://localhost:8001/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"city": "Paris"}}'

# Override capture mode
curl -X POST http://localhost:8001/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"city": "Tokyo"}, "capture_override": {"mode": "full"}}'
```

## Troubleshooting

- **Missing deployment ID**: set `ZENML_PIPELINE_DEPLOYMENT_ID`.
- **Slow performance**: ensure `capture="none"` for run-only mode.
- **Import errors**: run-only mode bypasses some ZenML integrations that aren't needed for serving.
- **Memory leaks**: serving contexts are automatically cleared per request.
- **Multi-worker issues**: ContextVar isolation ensures thread safety.

## Architecture Comparison

| Feature | Run-Only Mode | Full Tracking |
|---------|---------------|---------------|
| **Latency** | Milliseconds | Seconds |
| **DB Writes** | None | Full tracking |  
| **FS Writes** | None | Artifacts |
| **Memory** | Minimal | Standard |
| **Debugging** | Limited | Complete |
| **Production** | ✅ Optimal | For experimentation |

Choose run-only for production serving, full tracking for development and debugging.