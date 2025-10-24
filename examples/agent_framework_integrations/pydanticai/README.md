# PydanticAI + ZenML

PydanticAI type-safe agents integrated with ZenML for structured AI applications.

## 🚀 Quick Run

```bash
export OPENAI_API_KEY="your-api-key-here"
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
```

Initialize ZenML and login:
```bash
zenml init
zenml login
```

Run the pipeline:
```bash
python run.py
```

## 🌐 Pipeline Deployment

Deploy this agent as a real-time HTTP service:

```bash
# Deploy the pipeline as an HTTP service
zenml pipeline deploy run.agent_pipeline --name pydantic-ai-agent

# Invoke via CLI
zenml deployment invoke pydantic-ai-agent --query="Plan a weekend trip to San Francisco"

# Invoke via HTTP API
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"query": "What are the best restaurants in New York?"}}'
```

## ✨ Features

- **Type Safety**: Pydantic models for structured agent responses
- **Simple API**: Clean `run_sync()` interface for synchronous execution
- **Tool Integration**: Built-in support for function calling
- **Real-time Deployment**: Deploy as HTTP API for instant responses
- **ZenML Orchestration**: Full pipeline tracking and artifact management