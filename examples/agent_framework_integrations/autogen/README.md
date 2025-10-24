# Autogen + ZenML

Multi-agent conversation framework integrated with ZenML for travel planning with collaborative agents.

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
zenml pipeline deploy agent_pipeline --name autogen-service

# Invoke via CLI
zenml deployment invoke autogen-service --destination="Tokyo" --days=3

# Invoke via HTTP API
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"destination": "Tokyo", "days": 3}}'
```

## ✨ Features

- **Multi-Agent Collaboration**: Weather specialist and travel advisor agents
- **Async Runtime Management**: Proper agent lifecycle with cleanup
- **Travel Planning**: Comprehensive itinerary generation with weather integration
- **Real-time Deployment**: Deploy as HTTP API for instant responses
- **ZenML Orchestration**: Full pipeline tracking and artifact management