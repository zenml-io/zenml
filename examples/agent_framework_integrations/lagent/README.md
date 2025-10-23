# lagent + ZenML

## 中文快速开始 / Chinese Quick Start

lagent 是上海人工智能实验室（InternLM）开发的轻量级智能体框架，支持 ReAct、AutoGPT 等多种智能体模式。

### 安装和运行
```bash
export OPENAI_API_KEY="your-api-key-here"
cd lagent/
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
python run.py
```

### 主要特性
- 🔄 支持 ReAct 推理模式，多轮推理和函数调用
- 🐍 内置 Python 解释器工具
- 🤖 支持 InternLM 模型和 OpenAI 兼容接口
- ⚡ 轻量级设计，仅需 20 行代码即可构建智能体
- 📊 完整的工件管理和追踪

---

## English Documentation

lagent ReAct agent integrated with ZenML for production-grade orchestration.

## Run
```bash
export OPENAI_API_KEY="your-api-key-here"
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
python run.py
```

## Features
- ReAct reasoning pattern with iterative problem solving
- Built-in Python interpreter for code execution
- Support for OpenAI and InternLM models
- Lightweight framework requiring minimal code
- ActionExecutor for managing multiple tools
- Production-ready agent orchestration with ZenML

## About lagent

lagent is a lightweight open-source agent framework by Shanghai AI Laboratory (InternLM). It provides:
- 🔄 **Multiple Agent Patterns**: ReAct, AutoGPT, ReWOO
- 🛠️ **Built-in Tools**: Python interpreter, Google search, API calls
- 🔌 **Flexible Design**: Easy to add custom actions
- ⚡ **Async Support**: Both sync and async interfaces
- 🎯 **Simple API**: Build agents with just 20 lines of code

Learn more at the [official repository](https://github.com/InternLM/lagent).
