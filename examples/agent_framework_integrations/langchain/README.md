# LangChain + ZenML

LangChain agent chain integrated with ZenML for document summarization and web content processing.

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
zenml pipeline deploy agent_pipeline --name langchain-service

# Invoke via CLI
zenml deployment invoke langchain-service --query="Summarize: https://docs.zenml.io/"

# Invoke via HTTP API
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"query": "Summarize: https://your-url-here.com"}}'
```

## ✨ Features

- **Document Summarization**: Extract and summarize web content
- **LangChain Integration**: Leverages LangChain's WebBaseLoader and chains
- **Real-time Deployment**: Deploy as HTTP API for instant responses
- **ZenML Orchestration**: Full pipeline tracking and artifact management