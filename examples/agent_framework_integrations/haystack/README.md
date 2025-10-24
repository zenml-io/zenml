# Haystack + ZenML

Haystack RAG pipeline integrated with ZenML for intelligent document retrieval and question answering.

## 🚀 Quick Run

```bash
export OPENAI_API_KEY="your-api-key-here"
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
python run.py
```

## 🌐 Pipeline Deployment

Deploy this RAG system as a real-time HTTP service:

```bash
# Deploy the pipeline as an HTTP service
zenml pipeline deploy agent_pipeline --name haystack-rag-service

# Invoke via CLI
zenml deployment invoke haystack-rag-service --question="What city is home to the Eiffel Tower?"

# Invoke via HTTP API
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"question": "What is the capital of France?"}}'
```

## ✨ Features

- **Retrieval-Augmented Generation**: Combines document retrieval with LLM generation
- **Component-Based Architecture**: Modular pipeline with retrievers, prompt builders, and generators
- **In-Memory Document Store**: Fast BM25-based retrieval from preloaded documents
- **Real-time Deployment**: Deploy as HTTP API for instant Q&A responses
- **ZenML Orchestration**: Full pipeline tracking and artifact management