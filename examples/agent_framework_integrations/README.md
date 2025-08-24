<br />
<div align="center">
  <a href="https://zenml.io">
    <img src="../../docs/book/.gitbook/assets/header.png" alt="ZenML Logo" width="600">
  </a>

<h3 align="center">Agent Frameworks Integration Examples</h3>

  <p align="center">
    Systematic agent development with ZenML
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

# 🤖 ZenML Agent Development Platform

This collection demonstrates how to use ZenML as your **agent development platform** - applying the same systematic development practices you use for traditional ML to agent development. Each example shows how any agent framework can benefit from ZenML's experiment tracking, evaluation workflows, and deployment capabilities.

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
| [Google ADK](google-adk/) | 🧠 Gemini | Google AI agents, Gemini models | google-adk, gemini |
| [Haystack](haystack/) | 🔍 RAG | Retrieval pipelines, Document processing | haystack, openai |
| [LangChain](langchain/) | 🔗 Chains | Runnable chains, Tool composition | langchain, openai |
| [LangGraph](langgraph/) | 🕸️ Graphs | ReAct agents, Graph workflows | langgraph, openai |
| [LlamaIndex](llama_index/) | 📚 Functions | Function agents, Async execution | llama-index, openai |
| [OpenAI Agents SDK](openai_agents_sdk/) | 🏗️ Structured | Official OpenAI agents, Structured execution | openai-agents, openai |
| [PydanticAI](pydanticai/) | ✅ Type-Safe | Type-safe agents, Validation | pydantic-ai, openai |
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
- **Google ADK**: Gemini-powered agents with simple calls

### Advanced Orchestration
- **LangChain**: Composable chains with tool integration
- **LangGraph**: ReAct pattern with graph-based workflows
- **Semantic Kernel**: Plugin-based architecture

### Specialized Use Cases
- **Haystack**: RAG pipelines with retrieval components
- **LlamaIndex**: Function agents with async capabilities
- **OpenAI Agents SDK**: Structured execution with OpenAI

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

## 📖 Learn More

| Resource | Description |
|----------|-------------|
| 🤖 **[Agent Guide]** | Complete guide to agent development with ZenML |
| 📊 **[LLM Evaluation]** | Proven evaluation patterns for agents and LLMs |
| 🧘 **[ZenML 101]** | New to ZenML? Start here! |
| ⚛ **[Core Concepts]** | Understand ZenML fundamentals |
| 📓 **[Documentation]** | Full ZenML documentation |
| 📒 **[API Reference]** | Detailed API documentation |
| ⚽ **[Examples]** | More ZenML examples |

[Agent Guide]: https://docs.zenml.io/user-guide/agent-guide
[LLM Evaluation]: https://docs.zenml.io/user-guide/llmops-guide/evaluation
[ZenML 101]: https://docs.zenml.io/user-guide/starter-guide
[Core Concepts]: https://docs.zenml.io/getting-started/core-concepts
[Documentation]: https://docs.zenml.io/
[API Reference]: https://sdkdocs.zenml.io/
[Examples]: https://github.com/zenml-io/zenml/tree/main/examples

---

*This collection demonstrates how ZenML transforms agent development into a systematic, trackable workflow - applying the same rigor you use for traditional ML to agent development.*