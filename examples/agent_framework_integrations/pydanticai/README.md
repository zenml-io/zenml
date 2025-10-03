# PydanticAI + ZenML

PydanticAI type-safe agents integrated with ZenML.

## Run
```bash
export OPENAI_API_KEY="your-api-key-here"
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
python run.py
```

## Features
- Type-safe agent implementation
- Simple `run_sync()` API
- Built-in tool integration