# Google ADK + ZenML

Google Agent Development Kit (ADK) with Gemini integration through ZenML for intelligent tool calling.

## 🚀 Quick Run

```bash
export GOOGLE_API_KEY="your-gemini-api-key-here"
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
zenml pipeline deploy run.agent_pipeline --name google-adk-agent

# Invoke via CLI
zenml deployment invoke google-adk-agent --query="What's the weather like in Tokyo?"

# Invoke via HTTP API
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"query": "What time is it in New York right now?"}}'
```

## ✨ Features

- **Gemini Integration**: Google's advanced LLM via Agent Development Kit
- **Tool Calling**: Weather and current time tools with Python functions
- **Docker Orchestration**: Containerized execution with ZenML pipeline
- **Real-time Deployment**: Deploy as HTTP API for instant responses
- **ZenML Orchestration**: Full pipeline tracking and artifact management
