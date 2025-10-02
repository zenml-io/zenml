# LlamaIndex + ZenML

LlamaIndex Function Agent integrated with ZenML.

## Run
```bash
export OPENAI_API_KEY="your-api-key-here"
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
python run.py
```

## Features
- Function agents with async execution
- Multiple tool integration (weather, tip calculator)
- Async handling within ZenML steps