# LlamaIndex + ZenML

LlamaIndex Function Agent integrated with ZenML for intelligent reasoning with function calling capabilities.

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
zenml pipeline deploy agent_pipeline --name llama-index-service

# Invoke via CLI
zenml deployment invoke llama-index-service --query="What's the weather in New York and calculate a tip for a $50 bill?"

# Invoke via HTTP API
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"query": "Check the weather in London"}}'
```

## ✨ Features

- **ReAct Agent**: Advanced reasoning and acting capabilities with function calling
- **Multi-Tool Integration**: Weather checking and tip calculation tools
- **Async Execution**: Proper async handling within ZenML pipeline steps
- **Real-time Deployment**: Deploy as HTTP API for instant responses
- **ZenML Orchestration**: Full pipeline tracking and artifact management