# Semantic Kernel + ZenML

Microsoft Semantic Kernel integrated with ZenML for AI orchestration and plugin-based agent capabilities.

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
zenml pipeline deploy agent_pipeline --name semantic-kernel-service

# Invoke via CLI
zenml deployment invoke semantic-kernel-service --query="What is the weather in Tokyo?"

# Invoke via HTTP API
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"query": "Check the weather in London"}}'
```

## ✨ Features

- **Plugin-Based Architecture**: Extensible design with `@kernel_function` decorators
- **Automatic Function Calling**: Seamless integration of tools and functions
- **AI Orchestration**: Microsoft's enterprise-grade AI orchestration platform
- **Real-time Deployment**: Deploy as HTTP API for instant responses
- **ZenML Orchestration**: Full pipeline tracking and artifact management