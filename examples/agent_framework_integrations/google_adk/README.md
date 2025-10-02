# Google ADK + ZenML

Google Agent Development Kit (ADK) integrated with ZenML.

## Run
```bash
export GOOGLE_API_KEY="your-gemini-api-key-here"
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
python run.py
```

## Features
- Gemini-powered agent via Google ADK
- Python tool calling (weather + current time tools)
- Orchestrated with a ZenML pipeline and Docker settings
- ExternalArtifact pattern for easy parameterization
