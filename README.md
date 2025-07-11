<div align="center">
  <img referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=0fcbab94-8fbe-4a38-93e8-c2348450a42e" />
  <h1 align="center">MLOps for Reliable AI - From Classical ML to Agents</h1>
  <h3 align="center">Your unified toolkit for shipping everything from decision trees to complex AI agents, built on the MLOps principles you already trust.</h3>
</div>

<div align="center">

  <!-- PROJECT LOGO -->
  <br />
    <a href="https://zenml.io">
      <img alt="ZenML Logo" src="docs/book/.gitbook/assets/header.png" alt="ZenML Logo">
    </a>
  <br />

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
[downloads-shield]: https://img.shields.io/pypi/dm/zenml?color=431D93
[downloads-url]: https://pypi.org/project/zenml/
[contributors-shield]: https://img.shields.io/github/contributors/zenml-io/zenml?color=7A3EF4
[contributors-url]: https://github.com/zenml-io/zenml/graphs/contributors
[license-shield]: https://img.shields.io/github/license/zenml-io/zenml?color=9565F6
[license-url]: https://github.com/zenml-io/zenml/blob/main/LICENSE

<div align="center">
<p>
    <a href="https://zenml.io/features">Features</a> •
    <a href="https://zenml.io/roadmap">Roadmap</a> •
    <a href="https://github.com/zenml-io/zenml/issues">Report Bug</a> •
    <a href="https://zenml.io/pro">Sign up for ZenML Pro</a> •
    <a href="https://www.zenml.io/blog">Blog</a> •
    <a href="https://zenml.io/podcast">Podcast</a>
    <br />
    <br />
    🎉 For the latest release, see the <a href="https://github.com/zenml-io/zenml/releases">release notes</a>.
</p>
</div>

---

## 🚨 The Problem: MLOps Works for Models, But What About AI?

![No MLOps for modern AI](docs/book/.gitbook/assets/readme_problem.png)

You're an ML engineer. You've perfected deploying `scikit-learn` models and wrangling PyTorch jobs. Your MLOps stack is dialed in. But now, you're being asked to build and ship AI agents, and suddenly your trusted toolkit is starting to crack.

- **The Adaptation Struggle:** Your MLOps habits (rigorous testing, versioning, CI/CD) don’t map cleanly onto agent development. How do you version a prompt? How do you regression test a non-deterministic system? The tools that gave you confidence for models now create friction for agents.

- **The Divided Stack:** To cope, teams are building a second, parallel stack just for LLM-based systems. Now you’re maintaining two sets of tools, two deployment pipelines, and two mental models. Your classical models live in one world, your agents in another. It's expensive, complex, and slows everyone down.

- **The Broken Feedback Loop:** Getting an agent from your local environment to production is a slow, painful journey. By the time you get feedback on performance, cost, or quality, the requirements have already changed. Iteration is a guessing game, not a data-driven process.

## 💡 The Solution: One Framework for your Entire AI Stack

Stop maintaining two separate worlds. ZenML is a unified MLOps framework that extends the battle-tested principles you rely on for classical ML to the new world of AI agents. It’s one platform to develop, evaluate, and deploy your entire AI portfolio.

```python
# Morning: Your sklearn pipeline is still versioned and reproducible.
train_and_deploy_classifier()

# Afternoon: Your new agent evaluation pipeline uses the same logic.
evaluate_and_deploy_agent()

# Same platform. Same principles. New possibilities.
```

With ZenML, you're not replacing your knowledge; you're extending it. Use the pipelines and practices you already know to version, test, deploy, and monitor everything from classic models to the most advanced agents.

## 💻 See It In Action: Multi-Agent Architecture Comparison

**The Challenge:** Your team built three different customer service agents. Which one should go to production? With ZenML, you can build a reproducible pipeline to test them on real data and make a data-driven decision.

```python
from zenml import pipeline, step
import pandas as pd

@step
def load_real_conversations() -> pd.DataFrame:
    """Load actual customer queries from a feature store."""
    return load_from_feature_store("customer_queries_sample_1k")

@step
def run_architecture_comparison(queries: pd.DataFrame) -> dict:
    """Test three different agent architectures on the same data."""
    architectures = {
        "single_agent": SingleAgentRAG(),
        "multi_specialist": MultiSpecialistAgents(),
        "hierarchical": HierarchicalAgentTeam()
    }
    
    results = {}
    for name, agent in architectures.items():
        # ZenML automatically versions the agent's code, prompts, and tools
        results[name] = agent.batch_process(queries)
    return results

@step
def evaluate_and_decide(results: dict) -> str:
    """Evaluate results and generate a recommendation report."""
    # Compare architectures on quality, cost, latency, etc.
    evaluation_df = evaluate_results(results)
    
    # Generate a rich report comparing the architectures
    report = create_comparison_report(evaluation_df)
    
    # Automatically tag the winning architecture for a staging deployment
    winner = evaluation_df.sort_values("overall_score").iloc[0]
    tag_for_staging(winner["architecture_name"])
    
    return report

@pipeline
def compare_agent_architectures():
    """Your new Friday afternoon ritual: data-driven agent decisions."""
    queries = load_real_conversations()
    results = run_architecture_comparison(queries)
    report = evaluate_and_decide(results)

if __name__ == "__main__":
    # Run locally, compare results in the ZenML dashboard
    compare_agent_architectures()
```

**The Result:** A clear winner is selected based on data, not opinions. You have full lineage from the test data and agent versions to the final report and deployment decision.

## 🔄 The AI Development Lifecycle with ZenML

### From Chaos to Process

![Development lifecycle](docs/book/.gitbook/assets/readme_development_lifecycle.png)

<details>
  <summary><b>Click to see your new, structured workflow</b></summary>

### Your New Workflow

**Monday: Quick Prototype**
```python
# Start with a local script, just like always
agent = LangGraphAgent(prompt="You are a helpful assistant...")
response = agent.chat("Help me with my order")
```

**Tuesday: Make it a Pipeline**
```python
# Wrap your code in a ZenML step to make it reproducible
@step
def customer_service_agent(query: str) -> str:
    return agent.chat(query)
```

**Wednesday: Add Evaluation**
```python
# Test on real data, not toy examples
@pipeline
def eval_pipeline():
    test_data = load_production_samples()
    responses = customer_service_agent.map(test_data)
    scores = evaluate_responses(responses)
    track_experiment(scores)
```

**Thursday: Compare Architectures**
```python
# Make data-driven architecture decisions
results = compare_architectures(
    baseline="current_prod",
    challenger="new_multiagent_v2"
)
```

**Friday: Ship with Confidence**
```python
# Deploy the new agent with the same command you use for ML models
python agent_deployment.py --env=prod --model="customer_service:challenger"
```
</details>

## 🚀 Get Started (5 minutes)

### For ML Engineers Ready to Tame AI

```bash
# You know this drill
pip install zenml  # Includes LangChain, LlamaIndex integrations
zenml integration install langchain llamaindex

# Initialize (your ML pipelines still work!)
zenml init

# Pull our agent evaluation template
zenml init --template agent-evaluation-starter
```

### Your First AI Pipeline

```python
# look_familiar.py
from zenml import pipeline, step

@step
def run_my_agent(test_queries: list[str]) -> list[str]:
    """Your existing agent code, now with MLOps superpowers."""
    # Use ANY framework - LangGraph, CrewAI, raw OpenAI
    agent = YourExistingAgent()
    
    # Automatic versioning of prompts, tools, code, and configs
    return [agent.run(q) for q in test_queries]

@step
def evaluate_responses(queries: list[str], responses: list[str]) -> dict:
    """LLM judges + your custom business metrics."""
    quality = llm_judge(queries, responses)
    latency = measure_response_times()
    costs = calculate_token_usage()
    
    return {
        "quality": quality.mean(),
        "p95_latency": latency.quantile(0.95),
        "cost_per_query": costs.mean()
    }

@pipeline
def my_first_agent_pipeline():
    # Look ma, no YAML!
    queries = ["How do I return an item?", "What's your refund policy?"]
    responses = run_my_agent(queries)
    metrics = evaluate_responses(queries, responses)
    
    # Metrics are auto-logged, versioned, and comparable in the dashboard
    return metrics

if __name__ == "__main__":
    my_first_agent_pipeline()
    print("Check your dashboard: http://localhost:8080")
```

## 📚 Learn More

### 🖼️ Getting Started Resources

The best way to learn about ZenML is through our comprehensive documentation and tutorials:

- **[Starter Guide](https://docs.zenml.io/user-guides/starter-guide)** - From zero to production in 30 minutes
- **[LLMOps Guide](https://docs.zenml.io/user-guides/llmops-guide)** - Specific patterns for LLM applications
- **[SDK Reference](https://sdkdocs.zenml.io/)** - Complete API documentation

For visual learners, start with this 11-minute introduction:

[![Introductory Youtube Video](docs/book/.gitbook/assets/readme_youtube_thumbnail.png)](https://www.youtube.com/watch?v=wEVwIkDvUPs)

### 📖 Production Examples

1. **[E2E Batch Inference](examples/e2e/)** - Complete MLOps pipeline with feature engineering
2. **[LLM RAG Pipeline](https://github.com/zenml-io/zenml-projects/tree/main/llm-complete-guide)** - Production RAG with evaluation loops
3. **[Agentic Workflow (Deep Research)](https://github.com/zenml-io/zenml-projects/tree/main/deep_research)** - Orchestrate your agents with ZenML
4. **[Fine-tuning Pipeline](https://github.com/zenml-io/zenml-projects/tree/main/gamesense)** - Fine-tune and deploy LLMs

### 🏢 Deployment Options

**For Teams:**
- **[Self-hosted](https://docs.zenml.io/getting-started/deploying-zenml)** - Deploy on your infrastructure with Helm/Docker
- **[ZenML Pro](https://cloud.zenml.io/?utm_source=readme)** - Managed service with enterprise support (free trial)

**Infrastructure Requirements:**
- Kubernetes cluster (or local Docker)
- Object storage (S3/GCS/Azure)
- PostgreSQL database
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
- 🎙 [Podcast](https://zenml.io/podcast) - Interviews with ML practitioners

## ❓ FAQs from ML Engineers Like You

**Q: "Do I need to rewrite my agents or models to use ZenML?"**
A: No. Wrap your existing code in a `@step`. Keep using `scikit-learn`, PyTorch, LangGraph, LlamaIndex, or raw API calls. ZenML orchestrates your tools, it doesn't replace them.

**Q: "How is this different from LangSmith/Langfuse?"**
A: They provide excellent observability for LLM applications. We orchestrate the **full MLOps lifecycle for your entire AI stack**. With ZenML, you manage both your classical ML models and your AI agents in one unified framework, from development and evaluation all the way to production deployment.

**Q: "Can I use my existing MLflow/W&B setup?"**
A: Yes! We integrate with both. Your experiments, our pipelines.

**Q: "Is this just MLflow with extra steps?"**
A: No. MLflow tracks experiments. We orchestrate the entire development process – from training and evaluation to deployment and monitoring – for both models and agents.

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
