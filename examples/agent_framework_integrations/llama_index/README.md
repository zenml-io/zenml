# LlamaIndex + ZenML

LlamaIndex ReAct Agent integrated with ZenML for function calling and reasoning.

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
zenml pipeline deploy run.agent_pipeline --name llama-index-agent

# Invoke via CLI
zenml deployment invoke llama-index-agent --query="What's the weather like in Paris right now?"

# Invoke via HTTP API
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"query": "Calculate a 20% tip on a $85 dinner bill"}}'
```

## ✨ Features

- **ReAct Agent**: Advanced reasoning and acting with LlamaIndex
- **Function Tools**: Weather lookup and tip calculator integrations
- **Async Execution**: Proper async handling within ZenML steps
- **Real-time Deployment**: Deploy as HTTP API for instant responses
- **ZenML Orchestration**: Full pipeline tracking and artifact management