# AWS Strands + ZenML

AWS Strands agent framework integrated with ZenML.

## Run
```bash
export OPENAI_API_KEY="your-api-key-here"
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
python run.py
```

## Features
- Simple agent execution with callable interface
- Built-in tools using `@tool` decorator
- Math calculation capabilities