# LangGraph + ZenML

LangGraph ReAct agent integrated with ZenML for intelligent tool-calling workflows.

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
zenml pipeline deploy agent_pipeline --name langgraph-service

# Invoke via CLI
zenml deployment invoke langgraph-service --query="What is the weather in San Francisco?"

# Invoke via HTTP API
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"query": "What is the weather in San Francisco?"}}'
```

## ✨ Features

- **ReAct Agent Pattern**: Reasoning and Acting capabilities with tool calling
- **Graph-based Workflows**: LangGraph's state machine approach
- **Multi-tool Integration**: Search, calculation, and web tools
- **Real-time Deployment**: Deploy as HTTP API for instant responses
- **ZenML Orchestration**: Full pipeline tracking and artifact management