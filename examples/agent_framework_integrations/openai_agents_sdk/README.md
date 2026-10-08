# OpenAI Agents SDK + ZenML

OpenAI Agents SDK integrated with ZenML for structured agent execution and function calling.

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
zenml pipeline deploy run.agent_pipeline --name openai-agents-agent
```

Once deployed, you can interact with the service in multiple ways:

### 🎨 Custom Web UI
Navigate to the root endpoint in your browser to access an interactive web interface:
```
http://localhost:8000/
```

The UI provides:
- Free-form query input with example suggestions
- Real-time agent responses with markdown rendering
- Visual feedback and error handling

### 📚 API Documentation
FastAPI automatically generates interactive API documentation:
```
http://localhost:8000/docs    # Swagger UI
http://localhost:8000/redoc   # ReDoc alternative
```

### 🔧 Programmatic Access

**Via ZenML CLI:**
```bash
zenml deployment invoke openai-agents-agent --query="Tell me a fun fact about Tokyo"
```

**Via HTTP API:**
```bash
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"query": "What are some interesting facts about space exploration?"}}'
```

## ✨ Features

- **OpenAI Agents SDK**: Official SDK for structured agent execution
- **Function Tools**: Built-in tools with `@function_tool` decorator
- **Tracing & Monitoring**: Comprehensive execution tracking
- **Real-time Deployment**: Deploy as HTTP API for instant responses
- **ZenML Orchestration**: Full pipeline tracking and artifact management

## 🔁 Recording runs with Kitaru

The pipeline invokes the agent through the SDK's `Runner`. In production, swap it for `KitaruRunner` from the `kitaru-openai-agents` package and every run is recorded as a replayable session by [Kitaru](https://docs.zenml.io/kitaru), ZenML's sibling project for agents — then replay a real run against your real code with one thing changed and diff the pair. See the [OpenAI Agents SDK adapter docs](https://docs.zenml.io/kitaru/adapters/openai-agents).
