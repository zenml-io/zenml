# LangGraph + ZenML

LangGraph ReAct agent integrated with ZenML.

## Run
```bash
export OPENAI_API_KEY="your-api-key-here"
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
python run.py
```

## Features
- ReAct (Reasoning + Acting) agent pattern
- Message-based agent communication
- Built-in search and calculation tools