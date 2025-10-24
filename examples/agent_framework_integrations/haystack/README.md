# Haystack + ZenML

Haystack RAG pipeline integrated with ZenML for document retrieval and question answering.

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
zenml pipeline deploy run.agent_pipeline --name haystack-agent

# Invoke via CLI
zenml deployment invoke haystack-agent --query="What are the benefits of renewable energy?"

# Invoke via HTTP API
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"query": "Explain machine learning in simple terms"}}'
```

## ✨ Features

- **Retrieval-Augmented Generation**: RAG pipeline with document search
- **Component Architecture**: Modular Haystack components for flexibility
- **In-Memory Document Store**: Fast retrieval capabilities
- **Real-time Deployment**: Deploy as HTTP API for instant responses
- **ZenML Orchestration**: Full pipeline tracking and artifact management