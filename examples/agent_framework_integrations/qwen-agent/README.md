# Qwen-Agent + ZenML

## 中文快速开始 / Chinese Quick Start

Qwen-Agent 是阿里巴巴开源的智能体框架，支持函数调用、工具使用和多模态能力。

### 安装和运行
```bash
export OPENAI_API_KEY="your-api-key-here"
cd qwen-agent/
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
```

初始化 ZenML 并登录：
```bash
zenml init
zenml login
```

运行示例流水线：
```bash
python run.py
```

### 部署流水线（实时服务）
使用 ZenML 的部署功能将该流水线部署为 HTTP 实时服务：

```bash
# 将流水线部署为 HTTP 服务（引用 run.py 中的 agent_pipeline 符号）
zenml pipeline deploy run.agent_pipeline --name qwen-agent
```

通过 CLI 调用服务：
```bash
zenml deployment invoke qwen-agent --query="计算 12*8 然后再加上 10"
```

通过 HTTP API 调用服务：
```bash
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"query": "请计算 15*7 并加上 42"}}'
```

> 提示：
> - 该示例使用 OpenAI 兼容接口（在 `qwen_agent_impl.py` 中配置），需要设置环境变量 `OPENAI_API_KEY`。
> - 如果改用阿里云 DashScope，可按照 Qwen-Agent 文档设置 `DASHSCOPE_API_KEY` 并相应调整 LLM 配置。

---

## English Documentation

Qwen-Agent integrated with ZenML for production-grade agent orchestration.

## Run
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

Run the pipeline locally:
```bash
python run.py
```

## Pipeline Deployment

Deploy this agent as a real-time HTTP service:

```bash
# Deploy the pipeline as an HTTP service (referencing the agent_pipeline symbol in run.py)
zenml pipeline deploy run.agent_pipeline --name qwen-agent
```

Invoke via CLI:
```bash
zenml deployment invoke qwen-agent --query="Calculate 25*4 and add 10"
```

Invoke via HTTP API:
```bash
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"query": "Add 42 to 7*15"}}'
```

## Features
- Custom tool registration with `@register_tool` decorator
- Function calling capabilities with Qwen models
- Support for OpenAI-compatible APIs and DashScope
- Built-in calculator tool for mathematical operations
- Production-ready agent orchestration with ZenML

## About Qwen-Agent

Qwen-Agent is an open-source agent framework by Alibaba Cloud, built on the Qwen language models. It provides:
- 🔧 Easy tool creation and registration
- 🧠 Advanced function calling
- 🌐 MCP (Model Context Protocol) integration
- 📚 RAG (Retrieval-Augmented Generation) support
- 💻 Code interpreter capabilities

Learn more at the [official repository](https://github.com/QwenLM/Qwen-Agent).
