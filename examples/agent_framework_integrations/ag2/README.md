# AG2 + ZenML

AG2 multi-agent GroupChat framework integrated with ZenML for travel planning with collaborative specialist agents.

> **AG2 vs Microsoft AutoGen**: This directory uses the `ag2` PyPI package (`from autogen import AssistantAgent, GroupChat`). The sibling `autogen/` example uses Microsoft AutoGen (`from autogen_core import RoutedAgent`). They are separate projects with different APIs.

##  Quick Run

```bash
export OPENAI_API_KEY="your-api-key-here"
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
```

Initialize ZenML and login:
```bash
zenml init
zenml login
```

Run the pipeline:
```bash
python run.py
```
##  Pipeline Deployment

Deploy this agent as a real-time HTTP service:

```bash
# Deploy the pipeline as an HTTP service
zenml pipeline deploy run.agent_pipeline --name ag2-agent

# Invoke via CLI
zenml deployment invoke ag2-agent --city="Tokyo"

# Invoke via HTTP API
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"city": "Tokyo"}}'
```

## ✨ Features

- **GroupChat Orchestration**: Three agents collaborate via AG2's `GroupChat` and `GroupChatManager`
- **Tool Calling**: `@register_for_llm` + `@register_for_execution` decorators bind tools to each specialist
- **Travel Planning**: Weather and attractions specialists feed a coordinator that writes the final plan
- **Real-time Deployment**: Deploy as HTTP API for instant responses
- **ZenML Orchestration**: Full pipeline tracking and artifact management
