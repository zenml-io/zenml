# Google ADK + ZenML

Google Agent Development Kit (ADK) integrated with ZenML for weather reporting and time queries using Gemini.

## 🚀 Quick Run

```bash
export GOOGLE_API_KEY="your-gemini-api-key-here"
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
python run.py
```

## 🌐 Pipeline Deployment

Deploy this agent as a real-time HTTP service:

```bash
# Deploy the pipeline as an HTTP service
zenml pipeline deploy agent_pipeline --name google-adk-service

# Invoke via CLI
zenml deployment invoke google-adk-service --query="What's the weather in Paris and current time in Europe/Paris?"

# Invoke via HTTP API
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"query": "What time is it in Tokyo and what'\''s the weather there?"}}'
```

## ✨ Features

- **Gemini-Powered AI**: Uses Google's ADK with Gemini 2.0 Flash model
- **Multi-Tool Integration**: Weather reporting and timezone-aware time queries
- **Production Ready**: Robust error handling and defensive call patterns
- **Real-time Deployment**: Deploy as HTTP API for instant responses
- **ZenML Orchestration**: Full pipeline tracking and artifact management
