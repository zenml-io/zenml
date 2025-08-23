# Haystack + ZenML

Haystack RAG pipeline integrated with ZenML.

## Run
```bash
export OPENAI_API_KEY="your-api-key-here"
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
python run.py
```

## Features
- Retrieval-Augmented Generation (RAG) pipeline
- Component-based architecture
- In-memory document store with retrieval capabilities