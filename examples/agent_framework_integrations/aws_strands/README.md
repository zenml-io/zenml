# AWS Strands + ZenML

AWS Strands agent framework integrated with ZenML for mathematical calculations and problem solving.

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
zenml pipeline deploy run.agent_pipeline --name aws-strands-agent

# Invoke via CLI
zenml deployment invoke aws-strands-agent --query="Calculate the square root of 144"

# Invoke via HTTP API
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"query": "What is 15 * 23?"}}'
```

## ✨ Features

- **Mathematical Calculations**: Built-in arithmetic and advanced math operations
- **Tool Integration**: Uses `@tool` decorator for seamless function calling
- **Simple Agent Interface**: Straightforward callable interface for easy integration
- **Real-time Deployment**: Deploy as HTTP API for instant responses
- **ZenML Orchestration**: Full pipeline tracking and artifact management