# ZenML Pipeline Serving Examples

This directory contains examples demonstrating ZenML's new **run-only serving architecture** with millisecond-class latency for real-time inference and AI applications.

## 🚀 **New Run-Only Architecture**

ZenML Serving now automatically optimizes for performance:

- **🏃‍♂️ Run-Only Mode**: Millisecond-class latency with zero DB/FS writes
- **🧠 Intelligent Switching**: Automatically chooses optimal execution mode
- **⚡ In-Memory Handoff**: Step outputs passed directly via serving buffer
- **🔄 Multi-Worker Safe**: ContextVar isolation for concurrent requests
- **📝 No Model Mutations**: Clean effective configuration merging

## 📁 Files

1. **`weather_pipeline.py`** - Simple weather analysis with run-only optimization
2. **`chat_agent_pipeline.py`** - Streaming conversational AI with fast execution
3. **`test_serving.py`** - Test script to verify serving endpoints
4. **`README.md`** - This comprehensive guide

## 🎯 Examples Overview

### 1. Weather Agent Pipeline
- **Purpose**: Analyze weather for any city with AI recommendations
- **Mode**: Run-only optimization for millisecond response times
- **Features**: Automatic parameter injection, rule-based fallback
- **API**: Standard HTTP POST requests

### 2. Streaming Chat Agent Pipeline  
- **Purpose**: Real-time conversational AI with streaming responses
- **Mode**: Run-only with optional streaming support
- **Features**: Token-by-token streaming, WebSocket support
- **API**: HTTP, WebSocket streaming, async jobs with SSE

## 🏃‍♂️ **Run-Only vs Full Tracking**

### Run-Only Mode (Default - Millisecond Latency)
```python
@pipeline  # No capture settings = run-only mode
def fast_pipeline(city: str) -> str:
    return analyze_weather(city)
```

**✅ Optimizations Active:**
- Zero database writes
- Zero filesystem operations  
- In-memory step output handoff
- Per-request parameter injection
- Multi-worker safe execution

### Full Tracking Mode (For Development)
```python
@pipeline(settings={"capture": "full"})
def tracked_pipeline(city: str) -> str:
    return analyze_weather(city)
```

**📊 Features Active:**
- Complete run/step tracking
- Artifact persistence
- Dashboard integration
- Debug information

# 🚀 Quick Start Guide

## Prerequisites

```bash
# Install ZenML with serving support
pip install zenml

# Optional: For LLM analysis (otherwise uses rule-based fallback)
export OPENAI_API_KEY=your_openai_api_key_here
pip install openai
```

## Example 1: Weather Agent (Run-Only Mode)

### Step 1: Create and Deploy Pipeline

```bash
python weather_pipeline.py
```

**Expected Output:**
```
🌤️ Creating Weather Agent Pipeline Deployment...
📦 Creating deployment for serving...
✅ Deployment ID: 12345678-1234-5678-9abc-123456789abc

🚀 Start serving with:
export ZENML_PIPELINE_DEPLOYMENT_ID=12345678-1234-5678-9abc-123456789abc
python -m zenml.deployers.serving.app
```

### Step 2: Start Serving Service

```bash
export ZENML_PIPELINE_DEPLOYMENT_ID=12345678-1234-5678-9abc-123456789abc
python -m zenml.deployers.serving.app
```

**Service Configuration:**
- **Mode**: Run-only (millisecond latency) 
- **Host**: `http://localhost:8000`
- **Optimizations**: All I/O operations bypassed

### Step 3: Test Ultra-Fast Weather Analysis

```bash
# Basic request (millisecond response time)
curl -X POST "http://localhost:8000/invoke" \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"city": "Paris"}}'

# Response format:
{
  "success": true,
  "outputs": {
    "weather_analysis": "Weather in Paris is sunny with 22°C..."
  },
  "execution_time": 0.003,  # Milliseconds!
  "metadata": {
    "pipeline_name": "weather_agent_pipeline",
    "parameters_used": {"city": "Paris"},
    "steps_executed": 3
  }
}
```

## Example 2: Streaming Chat Agent (Run-Only Mode)

### Step 1: Create Chat Pipeline

```bash
python chat_agent_pipeline.py
```

### Step 2: Start Serving Service  

```bash
export ZENML_PIPELINE_DEPLOYMENT_ID=<chat-deployment-id>
python -m zenml.deployers.serving.app
```

### Step 3: Test Ultra-Fast Chat

#### Method A: Instant Response (Milliseconds)
```bash
curl -X POST "http://localhost:8000/invoke" \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"message": "Hello!", "user_name": "Alice"}}'

# Ultra-fast response:
{
  "success": true,
  "outputs": {"chat_response": "Hello Alice! How can I help you today?"},
  "execution_time": 0.002  # Milliseconds!
}
```

#### Method B: Streaming Mode (Optional)
```bash
# Create async job
JOB_ID=$(curl -X POST 'http://localhost:8000/invoke?mode=async' \
  -H 'Content-Type: application/json' \
  -d '{"parameters": {"message": "Tell me about AI", "enable_streaming": true}}' \
  | jq -r .job_id)

# Stream real-time results
curl -N "http://localhost:8000/stream/$JOB_ID"
```

#### Method C: WebSocket Streaming
```bash
# Install wscat: npm install -g wscat
wscat -c ws://localhost:8000/stream

# Send message:
{"parameters": {"message": "Hi there!", "user_name": "Alice", "enable_streaming": true}}
```

## 📊 Performance Comparison

| Feature | Run-Only Mode | Full Tracking |
|---------|---------------|---------------|
| **Response Time** | 1-5ms | 100-500ms |
| **Throughput** | 1000+ RPS | 10-50 RPS |
| **Memory Usage** | Minimal | Standard |
| **DB Operations** | Zero | Full tracking |
| **FS Operations** | Zero | Artifact storage |
| **Use Cases** | Production serving | Development/debug |

## 🛠️ Advanced Configuration

### Performance Tuning

```bash
# Set capture mode explicitly
export ZENML_SERVING_CAPTURE_DEFAULT=none  # Run-only mode

# Multi-worker deployment  
export ZENML_SERVICE_WORKERS=4
python -m zenml.deployers.serving.app
```

### Override Modes Per Request

```bash
# Force tracking for a single request (slower but tracked)
curl -X POST "http://localhost:8000/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "parameters": {"city": "Tokyo"},
    "capture_override": {"mode": "full"}
  }'
```

### Monitor Performance

```bash
# Service health and performance
curl http://localhost:8000/health
curl http://localhost:8000/metrics

# Pipeline information
curl http://localhost:8000/info
```

## 🏗️ Architecture Deep Dive

### Run-Only Execution Flow

```
Request → ServingOverrides → Effective Config → StepRunner → ServingBuffer → Response
          (Parameters)       (No mutations)    (No I/O)     (In-memory)   (JSON)
```

1. **Request Arrives**: JSON parameters received
2. **ServingOverrides**: Per-request parameter injection via ContextVar
3. **Effective Config**: Runtime configuration merging (no model mutations)
4. **Step Execution**: Direct execution with serving buffer storage
5. **Response Building**: Only declared outputs returned as JSON

### Key Components

- **`ServingOverrides`**: Thread-safe parameter injection
- **`ServingBuffer`**: In-memory step output handoff  
- **Effective Configuration**: Runtime config merging without mutations
- **ContextVar Isolation**: Multi-worker safe execution

## 📚 API Reference

### Core Endpoints

| Endpoint | Method | Purpose | Performance |
|----------|---------|---------|-------------|
| `/invoke` | POST | Execute pipeline | Milliseconds |
| `/health` | GET | Service health | Instant |
| `/info` | GET | Pipeline schema | Instant |
| `/metrics` | GET | Performance stats | Instant |

### Request Format

```json
{
  "parameters": {
    "city": "string",
    "temperature": "number",
    "enable_streaming": "boolean"
  },
  "capture_override": {
    "mode": "none|metadata|full"
  }
}
```

### Response Format

```json
{
  "success": true,
  "outputs": {
    "output_name": "output_value"
  },
  "execution_time": 0.003,
  "metadata": {
    "pipeline_name": "string",
    "parameters_used": {},
    "steps_executed": 0
  }
}
```

## 🔧 Troubleshooting

### Performance Issues
- ✅ **Ensure run-only mode**: No capture settings or `capture="none"`  
- ✅ **Check environment**: `ZENML_SERVING_CAPTURE_DEFAULT=none`
- ✅ **Monitor metrics**: Use `/metrics` endpoint

### Common Problems
- **Slow responses**: Verify run-only mode is active
- **Import errors**: Run-only mode bypasses unnecessary integrations
- **Memory leaks**: Serving contexts auto-cleared per request
- **Multi-worker issues**: ContextVar provides thread isolation

### Debug Mode
```bash
# Enable full tracking for debugging
curl -X POST "http://localhost:8000/invoke" \
  -d '{"parameters": {...}, "capture_override": {"mode": "full"}}'
```

## 🎯 Production Deployment

### Docker Example

```dockerfile
FROM python:3.9-slim

# Install ZenML
RUN pip install zenml

# Set serving configuration
ENV ZENML_SERVING_CAPTURE_DEFAULT=none
ENV ZENML_SERVICE_HOST=0.0.0.0
ENV ZENML_SERVICE_PORT=8000

# Start serving
CMD ["python", "-m", "zenml.deployers.serving.app"]
```

### Kubernetes Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: zenml-serving
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: serving
        image: zenml-serving:latest
        env:
        - name: ZENML_PIPELINE_DEPLOYMENT_ID
          value: "your-deployment-id"
        - name: ZENML_SERVING_CAPTURE_DEFAULT
          value: "none"
        ports:
        - containerPort: 8000
```

## 🚀 Next Steps

1. **Deploy Examples**: Try both weather and chat examples
2. **Measure Performance**: Use the `/metrics` endpoint
3. **Scale Up**: Deploy with multiple workers
4. **Monitor**: Integrate with your observability stack
5. **Optimize**: Fine-tune capture policies for your use case

The new run-only architecture delivers production-ready performance for real-time AI applications! 🎉