# LangChain + ZenML

LangChain agent chain integrated with ZenML for tool-enhanced conversational AI.

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
zenml pipeline deploy run.agent_pipeline --name langchain-agent

# Invoke via CLI
zenml deployment invoke langchain-agent --query="Calculate 15 * 23 and explain the result"

# Invoke via HTTP API
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"query": "Search for recent news about AI developments"}}'
```

## ✨ Features

- **Runnable Chains**: Composable chain architecture with pipe operators
- **Tool Integration**: Math calculations and web search capabilities
- **Agent Framework**: LangChain's agent paradigm for reasoning
- **Real-time Deployment**: Deploy as HTTP API for instant responses
- **ZenML Orchestration**: Full pipeline tracking and artifact management