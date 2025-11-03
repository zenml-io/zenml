# CrewAI + ZenML

CrewAI multi-agent crew framework integrated with ZenML for collaborative content creation.

## 🚀 Quick Run

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

## 🌐 Pipeline Deployment

Deploy this agent as a real-time HTTP service:

```bash
# Deploy the pipeline as an HTTP service
zenml pipeline deploy run.agent_pipeline --name crewai-agent

# Invoke via CLI
zenml deployment invoke crewai-agent --topic="AI in Healthcare"

# Invoke via HTTP API
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"topic": "The Future of Quantum Computing"}}'
```

## ✨ Features

- **Multi-Agent Crew**: Research and writing agents working collaboratively
- **Task Delegation**: Automatic work distribution among crew members
- **Content Creation**: Article research and writing workflow
- **Real-time Deployment**: Deploy as HTTP API for instant responses
- **ZenML Orchestration**: Full pipeline tracking and artifact management