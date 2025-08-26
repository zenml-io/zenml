# Autogen + ZenML

Multi-agent conversation framework integrated with ZenML.

## Run
```bash
export OPENAI_API_KEY="your-api-key-here"
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
python run.py
```

## Features
- Multi-agent conversations with UserProxy and Assistant agents
- Async runtime management with proper cleanup
- Travel planning use case with collaborative agents