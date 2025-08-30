# ZenML Pipeline Serving Examples

This directory contains examples demonstrating how to serve ZenML pipelines as FastAPI endpoints with real-time streaming capabilities.

## 📁 Files

1. **`weather_pipeline.py`** - Simple weather analysis agent with LLM integration
2. **`chat_agent_pipeline.py`** - Streaming conversational AI chat agent 
3. **`test_serving.py`** - Test script to verify serving endpoints
4. **`README.md`** - This comprehensive guide

## 🎯 Examples Overview

### 1. Weather Agent Pipeline
- **Purpose**: Analyze weather for any city with AI recommendations
- **Features**: LLM integration, rule-based fallback, parameter injection
- **API Mode**: Standard HTTP POST requests

### 2. Streaming Chat Agent Pipeline  
- **Purpose**: Real-time conversational AI with streaming responses
- **Features**: Token-by-token streaming, WebSocket support, Server-Sent Events
- **API Modes**: HTTP, WebSocket streaming, async jobs with SSE streaming

## Setup (Optional: For LLM Analysis)

To use real LLM analysis instead of rule-based fallback:

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your_openai_api_key_here

# Install OpenAI package
pip install openai
```

If no API key is provided, the pipeline will use an enhanced rule-based analysis as fallback.

# 🚀 Quick Start Guide

## 🔧 Starting the Serving Service

ZenML serving supports multiple ways to start the service:

### Option 1: Modern Command-Line Arguments (Recommended)
```bash
# Basic usage with deployment ID
python -m zenml.serving --deployment_id <your-deployment-id>

# With custom configuration
python -m zenml.serving \
  --deployment_id <your-deployment-id> \
  --host 0.0.0.0 \
  --port 8080 \
  --workers 2 \
  --log_level debug
```

### Option 2: Legacy Environment Variables
```bash
export ZENML_PIPELINE_DEPLOYMENT_ID=<your-deployment-id>
export ZENML_SERVICE_HOST=0.0.0.0      # Optional
export ZENML_SERVICE_PORT=8080          # Optional  
export ZENML_SERVICE_WORKERS=2          # Optional
export ZENML_LOG_LEVEL=debug            # Optional
python -m zenml.serving
```

### Option 3: Advanced Entrypoint Configuration (For Integration)
```bash
# Using the serving entrypoint configuration class directly
python -m zenml.serving \
  --entrypoint_config_source zenml.serving.entrypoint_configuration.ServingEntrypointConfiguration \
  --deployment_id <your-deployment-id> \
  --host 0.0.0.0 \
  --port 8080
```

---

## Example 1: Weather Agent Pipeline

### Step 1: Create Pipeline Deployment (with pipeline-level capture defaults)

```bash
python weather_pipeline.py
```

This example pipeline is configured with pipeline-level capture settings in code:

```python
@pipeline(settings={
  "docker": docker_settings,
  "serving": {
    "capture": {
      "mode": "full",
      "artifacts": "full",
      "max_bytes": 262144,
      "redact": ["password", "token"],
    }
  },
})
def weather_agent_pipeline(city: str = "London") -> None:
    ...
```

It will print a deployment ID like: `12345678-1234-5678-9abc-123456789abc`.

### Step 2: Start Serving Service  

**Modern Command-Line Arguments (Recommended):**
```bash
python -m zenml.serving --deployment_id your_deployment_id_from_step_1
```

**Legacy Environment Variable Method:**
```bash
export ZENML_PIPELINE_DEPLOYMENT_ID=your_deployment_id_from_step_1
python -m zenml.serving
```

**Custom Configuration:**
```bash
python -m zenml.serving --deployment_id your_id --host 0.0.0.0 --port 8080 --workers 2 --log_level debug
```

Service starts on `http://localhost:8000` (or your custom port)

### Step 3: Test Weather Analysis

```bash
# Test with curl (endpoint defaults from pipeline settings)
curl -X POST "http://localhost:8000/invoke" \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"city": "Paris"}}'

# Override capture for a single call (per-call override wins over defaults)
curl -X POST "http://localhost:8000/invoke" \
  -H "Content-Type: application/json" \
  -d '{
        "parameters": {"city": "Tokyo"},
        "capture_override": {
          "mode": "sampled",
          "sample_rate": 0.25,
          "artifacts": "sampled",
          "max_bytes": 4096,
          "redact": ["api_key", "password"]
        }
      }'

# Or use test script
python test_serving.py
```

Global off-switch (ops): to disable all tracking regardless of policy, set:

```bash
export ZENML_SERVING_CREATE_RUNS=false
```

---

## Example 2: Streaming Chat Agent Pipeline

### Step 1: Create Chat Pipeline Deployment

```bash
python chat_agent_pipeline.py
```

**Expected Output:**
```
🤖 Creating Chat Agent Pipeline Deployment...

💡 Note: Skipping local test due to ZenML integration loading issues
📦 Creating deployment for serving...

✅ Deployment ID: f770327d-4ce0-4a6c-8033-955c2e990736
```

### Step 2: Start Serving Service

**Modern Command-Line Arguments (Recommended):**
```bash
python -m zenml.serving --deployment_id f770327d-4ce0-4a6c-8033-955c2e990736
```

**Legacy Environment Variable Method:**
```bash
export ZENML_PIPELINE_DEPLOYMENT_ID=f770327d-4ce0-4a6c-8033-955c2e990736  
python -m zenml.serving
```

### Step 3: Test Streaming Chat (Multiple Methods)

#### Method A: Simple HTTP Request
```bash
curl -X POST "http://localhost:8000/invoke" \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"message": "Hello!", "user_name": "Alice", "personality": "helpful"}}'
```

#### Method B: Async Job + SSE Streaming (Recommended)
```bash
# Step 1: Create async job
curl -X POST 'http://localhost:8000/invoke?mode=async' \
  -H 'Content-Type: application/json' \
  -d '{"parameters": {"message": "Tell me about AI", "user_name": "Alice"}}'

# Response: {"job_id": "job-123", ...}

# Step 2: Stream real-time results
curl http://localhost:8000/stream/job-123
```

#### Method C: WebSocket Streaming (Real-time bidirectional)
```bash
# Install wscat if needed: npm install -g wscat
wscat -c ws://localhost:8000/stream

# Send message:
{"parameters": {"message": "Hi there!", "user_name": "Alice", "enable_streaming": true}}
```

### Step 4: Monitor Job Status
```bash
# Check specific job
curl http://localhost:8000/jobs/job-123

# List all jobs  
curl http://localhost:8000/jobs

# Cancel a job
curl -X POST http://localhost:8000/jobs/job-123/cancel

# View metrics
curl http://localhost:8000/concurrency/stats
```

# 📚 API Reference

## Core Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Service overview with documentation |
| `/health` | GET | Health check and uptime |
| `/info` | GET | Pipeline schema and configuration |
| `/invoke` | POST | Execute pipeline (sync/async modes) |
| `/metrics` | GET | Execution statistics |

## Streaming & Job Management

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/stream` | WebSocket | Real-time bidirectional streaming |
| `/jobs/{job_id}` | GET | Get job status and results |
| `/jobs/{job_id}/cancel` | POST | Cancel running job |
| `/jobs` | GET | List jobs with filtering |
| `/stream/{job_id}` | GET | Server-Sent Events stream |
| `/concurrency/stats` | GET | Concurrency and performance metrics |

## Parameters

### Weather Pipeline
```json
{
  "parameters": {
    "city": "string"
  }
}
```

### Chat Agent Pipeline  
```json
{
  "parameters": {
    "message": "string",
    "user_name": "string (optional)",
    "personality": "helpful|creative|professional|casual (optional)",
    "enable_streaming": "boolean (optional)"
  }
}
```

# 🏗️ Architecture Overview

## How ZenML Serving Works

1. **📦 Pipeline Deployment**: Create deployment without execution
2. **🚀 Serving Service**: FastAPI loads deployment and exposes endpoints  
3. **⚡ Runtime Execution**: Each API call executes with different parameters
4. **🔄 Streaming Layer**: Real-time events via WebSocket/SSE for streaming pipelines

## Key Features

- **🎯 Parameter Injection**: Runtime parameter customization per request
- **🔄 Streaming Support**: Token-by-token streaming for conversational AI
- **⚖️ Load Management**: Concurrency limits and request queuing
- **📊 Job Tracking**: Async job lifecycle management with cancellation
- **🛡️ Thread Safety**: Cross-thread event publishing and state management
- **📈 Observability**: Comprehensive metrics and health monitoring

## Streaming Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client        │    │   FastAPI        │    │   Pipeline      │
│                 │    │   Serving        │    │   Execution     │
├─────────────────┤    ├──────────────────┤    ├─────────────────┤
│ HTTP POST       │───▶│ /invoke?mode=    │───▶│ DirectExecution │
│ mode=async      │    │ async            │    │ Engine          │
│                 │    │                  │    │                 │
│ Response:       │◀───│ {"job_id": ...}  │    │ Background      │
│ {"job_id":...}  │    │                  │    │ Thread          │
│                 │    │                  │    │                 │
│ SSE Stream:     │    │ /stream/{job_id} │    │ Event Callback  │
│ curl /stream/   │───▶│                  │◀───│ (Thread-Safe)   │
│ {job_id}        │    │ Server-Sent      │    │                 │
│                 │◀───│ Events           │    │ StreamManager   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Production Considerations

- **🔒 Security**: Add authentication and rate limiting
- **📈 Scaling**: Use multiple workers with shared job registry  
- **🗄️ Persistence**: Consider Redis for job state in multi-instance deployments
- **📊 Monitoring**: Integrate with observability tools (Prometheus, Grafana)
- **🚨 Error Handling**: Implement retry logic and circuit breakers

## 📜 Capture Policy Summary

- Precedence: per-call override > step annotations > pipeline settings > endpoint default (dashboard/CLI).
- Modes:
  - **none**: no runs/steps, no payloads, no artifacts
  - **metadata** (default): runs/steps, no payload previews
  - **errors_only**: runs/steps, payload previews only on failures
  - **sampled**: runs/steps, payload/artifact capture for a fraction of invocations
  - **full**: runs/steps, payload previews for all invocations
- Artifacts: `none|errors_only|sampled|full` (orthogonal to mode; disabled if mode=none).
- Sampling: deterministic per-invocation (based on invocation id).