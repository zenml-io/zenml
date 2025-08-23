# OpenAI Agents SDK + ZenML

OpenAI Agents SDK integrated with ZenML.

## Run
```bash
export OPENAI_API_KEY="your-api-key-here"
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
python run.py
```

## Features
- Structured agent execution with OpenAI API
- Function tools with `@function_tool` decorator
- Built-in tracing and monitoring