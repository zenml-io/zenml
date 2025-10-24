# OpenAI Agents SDK + ZenML

OpenAI Agents SDK integrated with ZenML for structured agent execution and function calling.

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
zenml pipeline deploy run.agent_pipeline --name openai-agents-agent

# Invoke via CLI
zenml deployment invoke openai-agents-agent --query="Tell me a fun fact about Tokyo"

# Invoke via HTTP API
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"query": "What are some interesting facts about space exploration?"}}'
```

## ✨ Features

- **OpenAI Agents SDK**: Official SDK for structured agent execution
- **Function Tools**: Built-in tools with `@function_tool` decorator
- **Tracing & Monitoring**: Comprehensive execution tracking
- **Real-time Deployment**: Deploy as HTTP API for instant responses
- **ZenML Orchestration**: Full pipeline tracking and artifact management