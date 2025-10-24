# CrewAI + ZenML

CrewAI multi-agent crew framework integrated with ZenML for collaborative travel planning.

## 🚀 Quick Run

```bash
export OPENAI_API_KEY="your-api-key-here"
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
python run.py
```

## 🌐 Pipeline Deployment

Deploy this crew as a real-time HTTP service:

```bash
# Deploy the pipeline as an HTTP service
zenml pipeline deploy agent_pipeline --name crewai-service

# Invoke via CLI
zenml deployment invoke crewai-service --city="Berlin"

# Invoke via HTTP API
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"city": "Tokyo"}}'
```

## ✨ Features

- **Multi-Agent Collaboration**: Weather specialist and travel advisor working together
- **Role-based Task Delegation**: Specialized agents with defined responsibilities
- **Sequential Task Execution**: Weather checking followed by travel recommendations
- **Real-time Deployment**: Deploy as HTTP API for instant responses
- **ZenML Orchestration**: Full crew tracking and artifact management