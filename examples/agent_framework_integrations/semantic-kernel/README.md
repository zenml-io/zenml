# Semantic Kernel + ZenML

Microsoft Semantic Kernel integrated with ZenML.

## Run
```bash
export OPENAI_API_KEY="your-api-key-here"
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
python run.py
```

## Features
- Plugin-based architecture with `@kernel_function`
- Automatic function calling capabilities
- Async chat completion with OpenAI integration