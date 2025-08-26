# LangChain + ZenML

LangChain agent chain integrated with ZenML.

## Run
```bash
export OPENAI_API_KEY="your-api-key-here"
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
python run.py
```

## Features
- Runnable chains with tool integration
- Math and web search capabilities
- Composable chain architecture with pipe operators