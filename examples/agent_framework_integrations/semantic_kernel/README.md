# Semantic Kernel + ZenML

Microsoft Semantic Kernel integrated with ZenML for plugin-based AI applications.

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
zenml pipeline deploy run.agent_pipeline --name semantic-kernel-agent

# Invoke via CLI
zenml deployment invoke semantic-kernel-agent --query="What's the weather forecast for this week?"

# Invoke via HTTP API
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"query": "Calculate compound interest on $1000 at 5% for 10 years"}}'
```

## ✨ Features

- **Plugin Architecture**: Modular design with `@kernel_function` decorators
- **Automatic Function Calling**: Seamless tool integration and invocation
- **Async Chat Completion**: OpenAI integration with async support
- **Real-time Deployment**: Deploy as HTTP API for instant responses
- **ZenML Orchestration**: Full pipeline tracking and artifact management