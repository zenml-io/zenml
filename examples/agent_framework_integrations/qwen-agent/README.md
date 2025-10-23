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
python run.py
```

### 主要特性
- 🛠️ 自定义工具注册（如示例中的计算器）
- 🤖 支持 Qwen 模型和 OpenAI 兼容接口
- 🔄 与 ZenML 无缝集成，实现生产级智能体编排
- 📊 完整的工件管理和追踪

---

## English Documentation

Qwen-Agent integrated with ZenML for production-grade agent orchestration.

## Run
```bash
export OPENAI_API_KEY="your-api-key-here"
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
python run.py
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
