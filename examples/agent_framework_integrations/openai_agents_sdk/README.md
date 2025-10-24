# OpenAI Agents SDK + ZenML

This example demonstrates how to integrate the OpenAI Agents SDK with ZenML for building and orchestrating AI agents with function tools.

## Setup

1. **Install dependencies:**
```bash
export OPENAI_API_KEY="your-api-key-here"
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
```

2. **Run the standalone example:**
```bash
python example_usage.py
```

3. **Run the ZenML pipeline:**
```bash
python run.py
```

## 🌐 Pipeline Deployment

Deploy this agent as a real-time HTTP service:

```bash
# Deploy the pipeline as an HTTP service
zenml pipeline deploy agent_pipeline --name openai-agents-service

# Invoke via CLI
zenml deployment invoke openai-agents-service --query="Tell me a fun fact about Tokyo"

# Invoke via HTTP API
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"query": "What'\''s the weather in Paris and tell me about the city?"}}'
```

## ✨ Features

- **Function Tools**: Custom Python functions decorated with `@function_tool` for agent capabilities
- **GPT-4o Mini Model**: Uses the efficient GPT-4o Mini model for cost-effective operations
- **ZenML Integration**: Full pipeline orchestration with artifact tracking and monitoring
- **Error Handling**: Robust error handling and logging for production use

## Agent Capabilities

The agent includes two function tools:

- `get_weather(city: str)`: Returns weather information for a specified city
- `get_city_info(city: str)`: Provides general facts and information about cities

## Code Structure

- `openai_agent.py`: Contains the agent definition with function tools
- `run.py`: ZenML pipeline for orchestrated execution
- `example_usage.py`: Standalone example for direct agent usage
- `requirements.txt`: Dependencies including `openai-agents>=0.4.1`

## Usage Example

```python
from agents import Runner
from openai_agent import agent

# Run the agent with a query
result = Runner.run_sync(agent, "What's the weather like in Tokyo?")
print(result.final_output)
```