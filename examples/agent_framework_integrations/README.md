<br />
<div align="center">
  <a href="https://zenml.io">
    <img src="../../docs/book/.gitbook/assets/header.png" alt="ZenML Logo" width="600">
  </a>

<h3 align="center">Agent Frameworks Integration Examples</h3>

  <p align="center">
    Production-ready agent orchestration with ZenML
    <br />
    <a href="https://zenml.io/features">Features</a>
    ·
    <a href="https://zenml.io/roadmap">Roadmap</a>
    ·
    <a href="https://github.com/zenml-io/zenml/issues">Report Bug</a>
    ·
    <a href="https://zenml.io/discussion">Vote New Features</a>
    ·
    <a href="https://blog.zenml.io/">Read Blog</a>
    <br />
    <br /> 
    <a href="https://zenml.io/slack">
    <img src="https://img.shields.io/badge/JOIN US ON SLACK-4A154B?style=for-the-badge&logo=slack&logoColor=white" alt="Slack">
    </a>
    <a href="https://www.linkedin.com/company/zenml/">
    <img src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn">
    </a>
    <a href="https://twitter.com/zenml_io">
    <img src="https://img.shields.io/badge/Twitter-1DA1F2?style=for-the-badge&logo=twitter&logoColor=white" alt="Twitter">
    </a>
  </p>
</div>

# 🤖 Agent Frameworks + ZenML

This collection demonstrates how to integrate popular agent frameworks with ZenML for production-grade AI agent orchestration. Each example follows consistent patterns and best practices, making it easy to adapt any framework for your specific use case.

## 🚀 Quick Start

Choose any framework and get started in minutes:

```bash
export OPENAI_API_KEY="your-api-key-here"
cd framework-name/
uv venv --python 3.11
source .venv/bin/activate  
uv pip install -r requirements.txt
python run.py
```

## 📊 Frameworks Overview

| Framework | Type | Key Features | Technologies |
|-----------|------|-------------|-------------|
| [Autogen](autogen/) | 🤝 Multi-Agent | Multi-agent conversations, Role-based collaboration | autogen, openai |
| [AWS Strands](aws-strands/) | ⚡ Simple | Direct agent calls, Built-in tools | aws-agents, bedrock |
| [CrewAI](crewai/) | 👥 Crews | Agent crews, Task delegation | crewai, openai |
| [Google ADK](google_adk/) | 🔮 Gemini | Gemini-powered agents with tool calling | google-adk, gemini |
| [Haystack](haystack/) | 🔍 RAG | Retrieval pipelines, Document processing | haystack, openai |
| [lagent](lagent/) | 🔄 ReAct | ReAct pattern, Python interpreter, Lightweight | lagent, openai, internlm |
| [LangChain](langchain/) | 🔗 Chains | Runnable chains, Tool composition | langchain, openai |
| [LangGraph](langgraph/) | 🕸️ Graphs | ReAct agents, Graph workflows | langgraph, openai |
| [LlamaIndex](llama_index/) | 📚 Functions | Function agents, Async execution | llama-index, openai |
| [OpenAI Agents SDK](openai_agents_sdk/) | 🏗️ Structured | Official OpenAI agents, Structured execution | openai-agents, openai |
| [PydanticAI](pydanticai/) | ✅ Type-Safe | Type-safe agents, Validation | pydantic-ai, openai |
| [Qwen-Agent](qwen-agent/) | 🧠 Function Call | Custom tools, MCP integration, Qwen models | qwen-agent, openai |
| [Semantic Kernel](semantic-kernel/) | 🧩 Plugins | Plugin architecture, Microsoft ecosystem | semantic-kernel, openai |

## 🎯 Core Patterns

All examples follow these established patterns:

### 🔧 Environment Setup
- **uv for environments**: `uv venv --python 3.11`
- **Fast installs**: `uv pip install -r requirements.txt`
- **Consistent Python version**: 3.11 across all frameworks

### 📦 Pipeline Architecture
```python
@pipeline
def agent_pipeline() -> str:
    # 1. External artifact input
    query = ExternalArtifact(value="Your query")
    
    # 2. Agent execution
    results = run_agent(query)
    
    # 3. Response formatting
    summary = format_response(results)
    
    return summary
```

### 🛡️ Error Handling
- Comprehensive try-catch blocks
- Status tracking with success/error states
- Graceful degradation for agent failures

### 📊 Artifact Management
- **Annotated outputs**: `Annotated[Type, "artifact_name"]`
- **ZenML integration**: Full pipeline orchestration
- **Artifact storage**: S3-backed artifact management

## 🏗️ Framework-Specific Features

### Multi-Agent Systems
- **Autogen**: Conversational multi-agent workflows
- **CrewAI**: Role-based agent crews with task delegation

### Simple Execution
- **AWS Strands**: Direct callable interface with `agent(query)`
- **PydanticAI**: Clean `agent.run_sync(query)` API
- **Google ADK**: `agent.run(query)` API

### Advanced Orchestration
- **LangChain**: Composable chains with tool integration
- **LangGraph**: ReAct pattern with graph-based workflows
- **Semantic Kernel**: Plugin-based architecture

### Specialized Use Cases
- **Haystack**: RAG pipelines with retrieval components
- **LlamaIndex**: Function agents with async capabilities
- **OpenAI Agents SDK**: Structured execution with OpenAI

## 🔄 Implementation Notes

### Production vs. Demos
**These examples demonstrate single-query execution for simplicity.** In production, ZenML's value comes from:
- **Batch processing**: Process hundreds/thousands of queries overnight
- **Agent evaluation**: Compare different frameworks on test datasets  
- **Data pipelines**: Use agents to process document collections
- **A/B testing**: Systematic comparison of agent configurations

For real-time serving, use FastAPI/Flask directly. Use ZenML for the operational layer.

### Async Frameworks
Some frameworks require async handling within ZenML steps:
- **LlamaIndex**: `asyncio.run(agent.run(query))`
- **Semantic Kernel**: Event loop management for chat completion

### Tool Integration
Different frameworks have varying tool patterns:
- **Decorators**: `@tool`, `@function_tool`, `@kernel_function`
- **Functions**: Regular Python functions as tools
- **Classes**: Tool classes with specific interfaces

### Response Extraction
Each framework returns different response types:
- **String responses**: Direct text output
- **Object responses**: `.output`, `.content`, `.final_output` attributes
- **Complex responses**: Nested structures requiring extraction

## 📋 Requirements

- **Python**: 3.11+
- **ZenML**: Latest version
- **UV**: For fast package management
- **OpenAI API Key**: Most examples use OpenAI (set `OPENAI_API_KEY`)

## 🆘 Getting Help

- 💬 [Join our Slack community](https://zenml.io/slack)
- 📖 [Check our documentation](https://docs.zenml.io/)
- 🐛 [Report issues](https://github.com/zenml-io/zenml/issues)
- 💡 [Request features](https://zenml.io/discussion)

## 🌟 About ZenML

ZenML is an extensible, open-source MLOps framework for creating production-ready ML pipelines. These agent framework integrations showcase ZenML's flexibility in orchestrating AI workflows beyond traditional ML use cases.

**Why ZenML for Agent Orchestration?**
- 🔄 **Reproducible workflows**: Version and track agent executions
- 📊 **Artifact management**: Store and version agent inputs/outputs
- 🎯 **Production ready**: Built-in monitoring, logging, and error handling
- 🔧 **Tool agnostic**: Works with any agent framework
- ☁️ **Cloud native**: Deploy anywhere with consistent behavior

## 📖 Learn More

| Resource | Description |
|----------|-------------|
| 🧘 **[ZenML 101]** | New to ZenML? Start here! |
| ⚛ **[Core Concepts]** | Understand ZenML fundamentals |
| 🤖 **[LLMOps Guide]** | Complete guide to LLMOps with ZenML |
| 📓 **[Documentation]** | Full ZenML documentation |
| 📒 **[API Reference]** | Detailed API documentation |
| ⚽ **[Examples]** | More ZenML examples |

[ZenML 101]: https://docs.zenml.io/user-guides/starter-guide
[Core Concepts]: https://docs.zenml.io/getting-started/core-concepts
[LLMOps Guide]: https://docs.zenml.io/user-guides/llmops-guide
[Documentation]: https://docs.zenml.io/
[SDK Reference]: https://sdkdocs.zenml.io/
[Examples]: https://github.com/zenml-io/zenml/tree/main/examples

---

*This collection demonstrates the power and flexibility of ZenML for
orchestrating diverse agent frameworks in production environments.*
