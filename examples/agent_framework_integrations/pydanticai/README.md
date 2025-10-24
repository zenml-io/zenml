# PydanticAI + ZenML

PydanticAI type-safe agents integrated with ZenML for reliable and structured AI interactions.

## 🚀 Quick Run

```bash
export OPENAI_API_KEY="your-api-key-here"
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
python run.py
```

## 🌐 Pipeline Deployment

Deploy this agent as a real-time HTTP service:

```bash
# Deploy the pipeline as an HTTP service
zenml pipeline deploy agent_pipeline --name pydanticai-service

# Invoke via CLI
zenml deployment invoke pydanticai-service --query="What is the secret data?"

# Invoke via HTTP API
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"query": "Tell me about your capabilities"}}'
```

## ✨ Features

- **Type-Safe Agents**: Structured and validated agent interactions with Pydantic
- **Simple API**: Clean `run_sync()` interface for synchronous execution
- **Tool Integration**: Built-in support for function calling and tools
- **Real-time Deployment**: Deploy as HTTP API for instant responses
- **ZenML Orchestration**: Full pipeline tracking and artifact management