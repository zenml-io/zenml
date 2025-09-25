<div align="center">

  <!-- PROJECT LOGO -->
  <br />
    <a href="https://zenml.io">
      <img src="docs/book/.gitbook/assets/header.png" alt="ZenML Header">
    </a>
  <br />
  <div align="center">
    <h3 align="center">Your unified toolkit for shipping everything from decision trees to complex AI agents.</h3>
  </div>

  [![PyPi][pypi-shield]][pypi-url]
  [![PyPi][pypiversion-shield]][pypi-url]
  [![PyPi][downloads-shield]][downloads-url]
  [![Contributors][contributors-shield]][contributors-url]
  [![License][license-shield]][license-url]

</div>

<!-- MARKDOWN LINKS & IMAGES -->
[pypi-shield]: https://img.shields.io/pypi/pyversions/zenml?color=281158
[pypi-url]: https://pypi.org/project/zenml/
[pypiversion-shield]: https://img.shields.io/pypi/v/zenml?color=361776
[downloads-shield]: https://img.shields.io/pepy/dt/zenml?color=431D93
[downloads-url]: https://pypi.org/project/zenml/
[contributors-shield]: https://img.shields.io/github/contributors/zenml-io/zenml?color=7A3EF4
[contributors-url]: https://github.com/zenml-io/zenml/graphs/contributors
[license-shield]: https://img.shields.io/github/license/zenml-io/zenml?color=9565F6
[license-url]: https://github.com/zenml-io/zenml/blob/main/LICENSE

<div align="center">
<p>
    <a href="https://zenml.io/projects">Projects</a> •
    <a href="https://zenml.io/roadmap">Roadmap</a> •
    <a href="https://github.com/zenml-io/zenml/issues">Report Bug</a> •
    <a href="https://zenml.io/pro">Sign up for ZenML Pro</a> •
    <a href="https://www.zenml.io/blog">Blog</a> •
    <br />
    <br />
    🎉 For the latest release, see the <a href="https://github.com/zenml-io/zenml/releases">release notes</a>.
</p>
</div>

---

ZenML is built for ML or AI Engineers working on traditional ML use-cases, LLM workflows, or agents, in a company setting.
At it's core, ZenML allows you to write **workflows (pipelines)** that run on any **infrastructure backend (stacks)**. You can embed any Pythonic logic within these pipelines, like training a model, or running an agentic loop. ZenML then operationalizes your application by:

1. Automatically containerizing and tracking your code.
2. Tracking individual runs with metrics, logs, and metadata.
3. Abstracting away infrastructure complexity.
4. Integrating your existing tools and infrastructure e.g. MLflow, Langgraph, Langfuse, Sagemaker, GCP Vertex, etc.
5. Allowing you to quickly iterate on experiments with an observable layer, in development and in production.

...amongst many other features.

ZenML is used by thousands of companies to run their AI workflows. Here are some featured ones:

LISTOFCOMPANIES
(please email support@zenml.io if you want to be featured)

## 🚀 Get Started (5 minutes)

### 🏗️ Architecture Overview

ZenML uses a **client-server architecture** with an integrated web dashboard ([zenml-io/zenml-dashboard](https://github.com/zenml-io/zenml-dashboard)) for pipeline visualization and management:

- **Local Development**: `pip install "zenml[server]"` - runs both client and server locally
- **Production**: Deploy server separately, connect with `pip install zenml` + `zenml login <server-url>`

```bash
# Install ZenML with server capabilities
pip install "zenml[server]"

# Install required dependencies
pip install scikit-learn openai numpy

# Initialize your ZenML repository
zenml init

# Start local server or connect to a remote one
zenml login

# Set OpenAI API key (optional)
export OPENAI_API_KEY=sk-svv....
```

### Your First Pipeline (2 minutes)

```python
# simple_pipeline.py
from zenml import pipeline, step
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from typing import Tuple
from typing_extensions import Annotated
import numpy as np

@step
def create_dataset() -> Tuple[
    Annotated[np.ndarray, "X_train"],
    Annotated[np.ndarray, "X_test"], 
    Annotated[np.ndarray, "y_train"],
    Annotated[np.ndarray, "y_test"]
]:
    """Generate a simple classification dataset."""
    X, y = make_classification(n_samples=100, n_features=4, n_classes=2, random_state=42)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    return X_train, X_test, y_train, y_test

@step
def train_model(X_train: np.ndarray, y_train: np.ndarray) -> RandomForestClassifier:
    """Train a simple sklearn model."""
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X_train, y_train)
    return model

@step
def evaluate_model(model: RandomForestClassifier, X_test: np.ndarray, y_test: np.ndarray) -> float:
    """Evaluate the model accuracy."""
    predictions = model.predict(X_test)
    return accuracy_score(y_test, predictions)

@step
def generate_summary(accuracy: float) -> str:
    """Use OpenAI to generate a model summary."""
    import openai

    client = openai.OpenAI()  # Set OPENAI_API_KEY environment variable
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{
            "role": "user", 
            "content": f"Write a brief summary of a ML model with {accuracy:.2%} accuracy."
        }],
        max_tokens=50
    )
    return response.choices[0].message.content

@pipeline
def simple_ml_pipeline():
    """A simple pipeline combining sklearn and OpenAI."""
    X_train, X_test, y_train, y_test = create_dataset()
    model = train_model(X_train, y_train)
    accuracy = evaluate_model(model, X_test, y_test)
    try:
        import openai  # noqa: F401
        generate_summary(accuracy)
    except ImportError:
        print("OpenAI is not installed. Skipping summary generation.")


if __name__ == "__main__":
    result = simple_ml_pipeline()
```

Run it:
```bash
export OPENAI_API_KEY="your-api-key-here"
python simple_pipeline.py
```

Deploy it (HTTP endpoint):

```bash
zenml pipeline deploy simple_ml_pipeline --port 8001

curl -s -X POST localhost:8001/invoke \
  -H 'Content-Type: application/json' \
  -d '{"parameters": {}}'
```

Open the interactive docs at http://localhost:8001/docs, check health at /health, and view metrics at /metrics.

## 🗣️ Chat With Your Pipelines: ZenML MCP Server

Stop clicking through dashboards to understand your ML workflows. The **[ZenML MCP Server](https://github.com/zenml-io/mcp-zenml)** lets you query your pipelines, analyze runs, and trigger deployments using natural language through Claude Desktop, Cursor, or any MCP-compatible client.

```
💬 "Which pipeline runs failed this week and why?"
📊 "Show me accuracy metrics for all my customer churn models"  
🚀 "Trigger the latest fraud detection pipeline with production data"
```

**Quick Setup:**
1. Download the `.dxt` file from [zenml-io/mcp-zenml](https://github.com/zenml-io/mcp-zenml)
2. Drag it into Claude Desktop settings
3. Add your ZenML server URL and API key
4. Start chatting with your ML infrastructure

The MCP (Model Context Protocol) integration transforms your ZenML metadata into conversational insights, making pipeline debugging and analysis as easy as asking a question. Perfect for teams who want to democratize access to ML operations without requiring dashboard expertise.

## 📚 Learn More

### 🖼️ Getting Started Resources

The best way to learn about ZenML is through our comprehensive documentation and tutorials:

- **[Your First AI Pipeline](https://docs.zenml.io/your-first-ai-pipeline)** - Build and evaluate an AI service in minutes
- **[Starter Guide](https://docs.zenml.io/user-guides/starter-guide)** - From zero to production in 30 minutes
- **[LLMOps Guide](https://docs.zenml.io/user-guides/llmops-guide)** - Specific patterns for LLM applications
- **[SDK Reference](https://sdkdocs.zenml.io/)** - Complete SDK reference

For visual learners, start with this 11-minute introduction:

[![Introductory Youtube Video](docs/book/.gitbook/assets/readme_youtube_thumbnail.png)](https://www.youtube.com/watch?v=wEVwIkDvUPs)

### 📖 Production Examples

1. **[Agent Architecture Comparison](examples/agent_comparison/)** - Compare AI agents with LangGraph workflows, LiteLLM integration, and automatic visualizations via custom materializers
2. **[Minimal Agent Production](examples/minimal_agent_production/)** - Document analysis service with pipelines, evaluation, and web UI
3. **[E2E Batch Inference](examples/e2e/)** - Complete MLOps pipeline with feature engineering
4. **[LLM RAG Pipeline](https://github.com/zenml-io/zenml-projects/tree/main/llm-complete-guide)** - Production RAG with evaluation loops
5. **[Agentic Workflow (Deep Research)](https://github.com/zenml-io/zenml-projects/tree/main/deep_research)** - Orchestrate your agents with ZenML
6. **[Fine-tuning Pipeline](https://github.com/zenml-io/zenml-projects/tree/main/gamesense)** - Fine-tune and deploy LLMs

### 🏢 Deployment Options

Pipeline deployment exposes a FastAPI service for your pipeline on your chosen compute. Start local, then scale to Docker or Kubernetes as needed.

For pipeline deployment (HTTP endpoints), start with the Quickstart:
- https://docs.zenml.io/getting-started/quickstart

**For Teams:**
- **[Self-hosted](https://docs.zenml.io/getting-started/deploying-zenml)** - Deploy on your infrastructure with Helm/Docker
- **[ZenML Pro](https://cloud.zenml.io/?utm_source=readme)** - Managed service with enterprise support (free trial)

**Infrastructure Requirements:**
- Docker (or Kubernetes for production)
- Object storage (S3/GCS/Azure)
- MySQL-compatible database (MySQL 8.0+ or MariaDB)
- _[Complete requirements](https://docs.zenml.io/getting-started/deploying-zenml/deploy-with-helm)_

### 🎓 Books & Resources

<div align="center">
  <a href="https://www.amazon.com/LLM-Engineers-Handbook-engineering-production/dp/1836200072">
    <img src="docs/book/.gitbook/assets/llm_engineering_handbook_cover.jpg" alt="LLM Engineer's Handbook Cover" width="200"/>
  </a>
  <a href="https://www.amazon.com/-/en/Andrew-McMahon/dp/1837631964">
    <img src="docs/book/.gitbook/assets/ml_engineering_with_python.jpg" alt="Machine Learning Engineering with Python Cover" width="200"/>
  </a>
</div>

ZenML is featured in these comprehensive guides to production AI systems.

## 🤝 Join ML Engineers Building the Future of AI

**Contribute:**
- 🌟 [Star us on GitHub](https://github.com/zenml-io/zenml/stargazers) - Help others discover ZenML
- 🤝 [Contributing Guide](CONTRIBUTING.md) - Start with [`good-first-issue`](https://github.com/issues?q=is%3Aopen+is%3Aissue+archived%3Afalse+user%3Azenml-io+label%3A%22good+first+issue%22)
- 💻 [Write Integrations](https://github.com/zenml-io/zenml/blob/main/src/zenml/integrations/README.md) - Add your favorite tools

**Stay Updated:**
- 🗺 [Public Roadmap](https://zenml.io/roadmap) - See what's coming next
- 📰 [Blog](https://zenml.io/blog) - Best practices and case studies
- 🎙 [Slack](https://zenml.io/slack) - Talk with AI practitioners

## ❓ FAQs from ML Engineers Like You

**Q: "Do I need to rewrite my agents or models to use ZenML?"**

A: No. Wrap your existing code in a `@step`. Keep using `scikit-learn`, PyTorch, LangGraph, LlamaIndex, or raw API calls. ZenML orchestrates your tools, it doesn't replace them.

**Q: "How is this different from LangSmith/Langfuse?"**

A: They provide excellent observability for LLM applications. We orchestrate the **full MLOps lifecycle for your entire AI stack**. With ZenML, you manage both your classical ML models and your AI agents in one unified framework, from development and evaluation all the way to production deployment.

**Q: "Can I use my existing MLflow/W&B setup?"**

A: Yes! ZenML integrates with both [MLflow](https://docs.zenml.io/stacks/experiment-trackers/mlflow) and [Weights & Biases](https://docs.zenml.io/stacks/experiment-trackers/wandb). Your experiments, our pipelines.

**Q: "Is this just MLflow with extra steps?"**

A: No. MLflow tracks experiments. We orchestrate the entire development process – from training and evaluation to deployment and monitoring – for both models and agents.

**Q: "How do I configure ZenML with Kubernetes?"**

A: ZenML integrates with Kubernetes through the native Kubernetes orchestrator, Kubeflow, and other K8s-based orchestrators. See our [Kubernetes orchestrator guide](https://docs.zenml.io/stacks/orchestrators/kubernetes) and [Kubeflow guide](https://docs.zenml.io/stacks/orchestrators/kubeflow), plus [deployment documentation](https://docs.zenml.io/getting-started/deploying-zenml/deploy-with-helm).

**Q: "What about cost? I can't afford another platform."**

A: ZenML's open-source version is free forever. You likely already have the required infrastructure (like a Kubernetes cluster and object storage). We just help you make better use of it for MLOps.

### 🛠 VS Code Extension

Manage pipelines directly from your editor:

<details>
  <summary>🖥️ VS Code Extension in Action!</summary>
  <div align="center">
  <img width="60%" src="docs/book/.gitbook/assets/zenml-extension-shortened.gif" alt="ZenML Extension">
</div>
</details>

Install from [VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=ZenML.zenml-vscode).

## 📜 License

ZenML is distributed under the terms of the Apache License Version 2.0. See
[LICENSE](LICENSE) for details.
