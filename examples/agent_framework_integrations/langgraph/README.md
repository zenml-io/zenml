# LangGraph + ZenML

LangGraph ReAct agent integrated with ZenML for sophisticated reasoning and action loops.

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
zenml pipeline deploy run.agent_pipeline --name langgraph-agent

# Invoke via CLI
zenml deployment invoke langgraph-agent --query="Research the population of Tokyo and calculate its density"

# Invoke via HTTP API
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"query": "What is the square root of 144 and why is it useful?"}}'
```

## ✨ Features

- **ReAct Pattern**: Reasoning + Acting agent architecture for complex tasks
- **Message-Based Communication**: Structured agent state management
- **Built-in Tools**: Search and calculation capabilities
- **Real-time Deployment**: Deploy as HTTP API for instant responses
- **ZenML Orchestration**: Full pipeline tracking and artifact management