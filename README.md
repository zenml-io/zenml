<div align="center">
  <img referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=0fcbab94-8fbe-4a38-93e8-c2348450a42e" />
  <h1 align="center">The Orchestration & Observability Layer for Production AI</h1>
  <h3 align="center">ZenML brings battle-tested MLOps practices to all your AI applications – from traditional ML to the latest LLMs – handling evaluation, monitoring, and deployment at scale.</h3>
</div>

<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->

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
  <!-- [![Build][build-shield]][build-url] -->
  <!-- [![CodeCov][codecov-shield]][codecov-url] -->

</div>

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->

[pypi-shield]: https://img.shields.io/pypi/pyversions/zenml?color=281158

[pypi-url]: https://pypi.org/project/zenml/

[pypiversion-shield]: https://img.shields.io/pypi/v/zenml?color=361776

[downloads-shield]: https://img.shields.io/pypi/dm/zenml?color=431D93

[downloads-url]: https://pypi.org/project/zenml/

[codecov-shield]: https://img.shields.io/codecov/c/gh/zenml-io/zenml?color=7A3EF4

[codecov-url]: https://codecov.io/gh/zenml-io/zenml

[contributors-shield]: https://img.shields.io/github/contributors/zenml-io/zenml?color=7A3EF4

[contributors-url]: https://github.com/zenml-io/zenml/graphs/contributors

[license-shield]: https://img.shields.io/github/license/zenml-io/zenml?color=9565F6

[license-url]: https://github.com/zenml-io/zenml/blob/main/LICENSE

[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555

[linkedin-url]: https://www.linkedin.com/company/zenml/

[twitter-shield]: https://img.shields.io/twitter/follow/zenml_io?style=for-the-badge

[twitter-url]: https://twitter.com/zenml_io

[slack-shield]: https://img.shields.io/badge/-Slack-black.svg?style=for-the-badge&logo=linkedin&colorB=555

[slack-url]: https://zenml.io/slack-invite

[build-shield]: https://img.shields.io/github/workflow/status/zenml-io/zenml/Build,%20Lint,%20Unit%20&%20Integration%20Test/develop?logo=github&style=for-the-badge

[build-url]: https://github.com/zenml-io/zenml/actions/workflows/ci.yml

---

Need help with documentation? Visit our [docs site](https://docs.zenml.io) for comprehensive guides and tutorials, or browse the [SDK reference](https://sdkdocs.zenml.io/) to find specific functions and classes.

## ⭐️ Show Your Support

If you find ZenML helpful or interesting, please consider giving us a star on GitHub. Your support helps promote the project and lets others know that it's worth checking out.

Thank you for your support! 🌟

[![Star this project](https://img.shields.io/github/stars/zenml-io/zenml?style=social)](https://github.com/zenml-io/zenml/stargazers)

## 🤸 Quickstart
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/zenml-io/zenml/blob/main/examples/quickstart/quickstart.ipynb)

[Install ZenML](https://docs.zenml.io/getting-started/installation) via [PyPI](https://pypi.org/project/zenml/). Python 3.9 - 3.12 is required:

```bash
pip install "zenml[server]" notebook
```

Take a tour with the guided quickstart by running:

```bash
zenml go
```

## Beyond the Demo: The Reality of Production AI

You've built an impressive POC with LangGraph, and your RAG demo is working flawlessly. But taking that next step into a production environment reveals a host of new challenges: running evaluation pipelines on every update, processing documents in batch, tracking costs across multiple LLM providers, and ensuring compliance with regulations like the EU AI Act.

This is where many AI projects stall. The transition from a prototype to a reliable, scalable system is complex, and it's a journey ZenML is built for. If you are one of the following, ZenML can help:

- **A platform team** trying to tame tool sprawl and provide a stable foundation for data scientists.
- **An enterprise** needing to run robust batch workflows for document processing or large-scale evaluations.
- **An organization in a regulated industry** (like finance or healthcare) that requires full data and model lineage for compliance.

ZenML provides the production-grade orchestration layer to connect your existing tools and solve these challenges, putting you back in control of your AI stack.

## What does ZenML add to your stack?

### Write Code Once, Run Anywhere

Your workflow logic shouldn't be tied to your infrastructure. ZenML lets you write portable pipelines that can be executed on your laptop for rapid iteration and then seamlessly run on any cloud stack for production workloads—without changing a single line of code.

```python
# Your standard pipeline code remains unchanged
from zenml import pipeline

@pipeline
def my_training_pipeline():
    # ... steps to train a model
    return model

if __name__ == "__main__":
    my_training_pipeline()
```

```bash
# Run locally for quick iteration
$ zenml stack set local_stack
$ python run.py

# Switch to the production cloud stack and run the exact same code
$ zenml stack set aws_production
$ python run.py
```

_**Visual idea:** A short GIF showing `zenml stack list`, `zenml stack set local_stack`, `python run.py`, then `zenml stack set aws_production`, `python run.py` again._

### Automatic Versioning for MLOps and LLMOps

ZenML automatically tracks every component of your AI workflow, from datasets and models to prompts and pipeline configurations. Whether you're training a classic `scikit-learn` classifier or evaluating a RAG pipeline, you get complete lineage and reproducibility, which is crucial for debugging, compliance (like the EU AI Act), and building trust in your systems.

```python
from zenml import log_metadata, step, pipeline, Model
from typing_extensions import Annotated
import pandas as pd

# A classifier placeholder for the example
from sklearn.base import BaseEstimator, ClassifierMixin
class Classifier(BaseEstimator, ClassifierMixin):
    def fit(self, X, y=None):
        return self
    def predict(self, X):
        return [1] * len(X)

# MLOps: A classic model training step with automatic versioning
@step(model=Model(name="sentiment_classifier", tags=["staging"]))
def model_trainer(data: pd.DataFrame) -> Annotated[Classifier, "sklearn_model"]:
    # ... training logic ...
    model = Classifier()
    return model

# LLMOps: An evaluation step logging custom metadata like cost
@step
def llm_evaluator(results: list) -> Annotated[float, "hallucination_score"]:
    # ... evaluation logic ...
    cost = len(results) * 0.001
  
    # Log custom metadata back to ZenML
    log_metadata({"total_eval_cost_usd": cost})

    hallucination_score = 0.1
    return hallucination_score
```

_**Visual idea:** A screenshot of the ZenML dashboard showing a model's version history or a pipeline run with artifacts and metadata like `total_cost_usd` visible._

## Build Production-Grade AI Workflows

### Unify Your Toolchain

ZenML integrates with the tools you already use, creating a seamless workflow from experimentation to production. Connect your favorite experiment tracker, alerter, or deployment tool with a single line of configuration.

```python
# before you run your pipeline
# $ zenml stack set alerter_stack

from zenml import pipeline, step
from zenml.hooks import alerter_failure_hook

@pipeline(experiment_tracker="my_mlflow_tracker")
def llm_finetuning_pipeline():
    # ... call your steps here
    pass

# Use integrations at the step level
@step(on_failure=alerter_failure_hook)
def llm_trainer():
    # Your training code here. MLflow autologging is enabled by the
    # pipeline-level experiment_tracker.
    ...

# The pipeline will automatically post to Slack if it fails
```
_**Visual idea:** A gallery of integration logos (MLflow, Slack, Kubeflow, etc.) or a diagram showing ZenML connecting various tools._

### Production-Grade MLOps: The Classic Way

Build robust, traditional machine learning pipelines for tasks like classification or regression. ZenML helps you automate model promotion based on performance, ensuring that only high-quality models make it to production.

```python
from zenml import pipeline, step, Model
from sklearn.ensemble import RandomForestClassifier

@step
def trainer() -> RandomForestClassifier:
    # X_train, y_train = load_some_data()
    model = RandomForestClassifier()
    # model.fit(X_train, y_train)
    return model

@step
def evaluator(model: RandomForestClassifier) -> float:
    # X_test, y_test = load_test_data()
    # accuracy = model.score(X_test, y_test)
    accuracy = 0.92
    return accuracy

@step(model=Model(name="credit_fraud_detector", license="Apache 2.0"))
def model_promoter(model: RandomForestClassifier, accuracy: float):
    if accuracy > 0.9:
        # The 'model' is automatically versioned and promoted
        print("Model promoted to staging!")
    else:
        print("Model performance too low. Not promoting.")

@pipeline
def fraud_detection_pipeline():
    model = trainer()
    accuracy = evaluator(model)
    model_promoter(model=model, accuracy=accuracy)
```
_**Visual idea:** A screenshot from the ZenML dashboard showing a model being promoted to a 'staging' or 'production' tag, highlighting the model versioning view._

### Scalable LLMOps: RAG Document Ingestion

Orchestrate complex LLM workflows like Retrieval-Augmented Generation (RAG). ZenML makes it easy to build and manage batch document processing pipelines that create and version vector store indexes for your AI applications.

```python
from zenml import pipeline, step
from typing_extensions import Annotated

@step
def load_and_chunk_docs() -> list:
    # Load documents from a source and chunk them
    return ["chunk1", "chunk2"]

@step
def generate_embeddings(chunks: list) -> list:
    # Generate embeddings using your chosen model
    return [[0.1, 0.2], [0.3, 0.4]]
    
@step
def build_vector_index(embeddings: list) -> Annotated[str, "vector_store_uri"]:
    # Create and save a FAISS or Chroma index
    return "path/to/vector_store"

@pipeline
def rag_ingestion_pipeline():
    chunks = load_and_chunk_docs()
    embeddings = generate_embeddings(chunks)
    build_vector_index(embeddings)
```
_**Visual idea:** A DAG visualization of the RAG pipeline from the ZenML dashboard, showing the flow from documents to a vector store artifact._


## 🖼️ Learning

The best way to learn about ZenML is the [docs](https://docs.zenml.io/). We recommend beginning with the [Starter Guide](https://docs.zenml.io/user-guide/starter-guide) to get up and running quickly.

If you are a visual learner, this 11-minute video tutorial is also a great start:

[![Introductory Youtube Video](docs/book/.gitbook/assets/readme_youtube_thumbnail.png)](https://www.youtube.com/watch?v=wEVwIkDvUPs)

And finally, here are some other examples and use cases for inspiration:

1. [E2E Batch Inference](examples/e2e/): Feature engineering, training, and inference pipelines for tabular machine learning.
2. [Basic NLP with BERT](examples/e2e_nlp/): Feature engineering, training, and inference focused on NLP.
3. [LLM RAG Pipeline with Langchain and OpenAI](https://github.com/zenml-io/zenml-projects/tree/main/zenml-support-agent): Using Langchain to create a simple RAG pipeline.
4. [Huggingface Model to Sagemaker Endpoint](https://github.com/zenml-io/zenml-projects/tree/main/huggingface-sagemaker): Automated MLOps on Amazon Sagemaker and HuggingFace
5. [LLMops](https://github.com/zenml-io/zenml-projects/tree/main/llm-complete-guide): Complete guide to do LLM with ZenML

## 📚 LLM-focused Learning Resources

1. [LL Complete Guide - Full RAG Pipeline](https://github.com/zenml-io/zenml-projects/tree/main/llm-complete-guide) - Document ingestion, embedding management, and query serving
2. [LLM Fine-Tuning Pipeline](https://github.com/zenml-io/zenml-projects/tree/main/zencoder) - From data prep to deployed model
3. [LLM Agents Example](https://github.com/zenml-io/zenml-projects/tree/main/zenml-support-agent) - Track conversation quality and tool usage

## 📚 Learn from Books

<div align="center">
  <a href="https://www.amazon.com/LLM-Engineers-Handbook-engineering-production/dp/1836200072">
    <img src="docs/book/.gitbook/assets/llm_engineering_handbook_cover.jpg" alt="LLM Engineer's Handbook Cover" width="200"/></img>
  </a>&nbsp;&nbsp;&nbsp;&nbsp;
  <a href="https://www.amazon.com/-/en/Andrew-McMahon/dp/1837631964">
    <img src="docs/book/.gitbook/assets/ml_engineering_with_python.jpg" alt="Machine Learning Engineering with Python Cover" width="200"/></img>
  </a>
  </br></br>
</div>

ZenML is featured in these comprehensive guides to modern MLOps and LLM engineering. Learn how to build production-ready machine learning systems with real-world examples and best practices.

## 🔋 Deploy ZenML

For full functionality ZenML should be deployed on the cloud to
enable collaborative features as the central MLOps interface for teams.

Read more about various deployment options [here](https://docs.zenml.io/getting-started/deploying-zenml).

Or, sign up for [ZenML Pro to get a fully managed server on a free trial](https://cloud.zenml.io/?utm_source=readme&utm_medium=referral_link&utm_campaign=cloud_promotion&utm_content=signup_link).

## Use ZenML with VS Code

ZenML has a [VS Code extension](https://marketplace.visualstudio.com/items?itemName=ZenML.zenml-vscode) that allows you to inspect your stacks and pipeline runs directly from your editor. The extension also allows you to switch your stacks without needing to type any CLI commands.

<details>
  <summary>🖥️ VS Code Extension in Action!</summary>
  <div align="center">
  <img width="60%" src="docs/book/.gitbook/assets/zenml-extension-shortened.gif" alt="ZenML Extension">
</div>
</details>

## 🗺 Roadmap

ZenML is being built in public. The [roadmap](https://zenml.io/roadmap) is a regularly updated source of truth for the ZenML community to understand where the product is going in the short, medium, and long term.

ZenML is managed by a [core team](https://zenml.io/company) of developers that are responsible for making key decisions and incorporating feedback from the community. The team oversees feedback via various channels,
and you can directly influence the roadmap as follows:

- Vote on your most wanted feature on our [Discussion
board](https://zenml.io/discussion).
- Start a thread in our [Slack channel](https://zenml.io/slack).
- [Create an issue](https://github.com/zenml-io/zenml/issues/new/choose) on our GitHub repo.

## 🙌 Contributing and Community

We would love to develop ZenML together with our community! The best way to get
started is to select any issue from the `[good-first-issue`
label](https://github.com/issues?q=is%3Aopen+is%3Aissue+archived%3Afalse+user%3Azenml-io+label%3A%22good+first+issue%22)
and open up a Pull Request! 

If you
would like to contribute, please review our [Contributing
Guide](CONTRIBUTING.md) for all relevant details.

## 🆘 Getting Help

The first point of call should
be [our Slack group](https://zenml.io/slack-invite/).
Ask your questions about bugs or specific use cases, and someone from
the [core team](https://zenml.io/company) will respond.
Or, if you
prefer, [open an issue](https://github.com/zenml-io/zenml/issues/new/choose) on
our GitHub repo.

## 🤖 AI-Friendly Documentation with llms.txt

ZenML implements the llms.txt standard to make our documentation more accessible to AI assistants and LLMs. Our implementation includes:

- Base documentation at [zenml.io/llms.txt](https://zenml.io/llms.txt) with core user guides
- Specialized files for different documentation aspects:
  - [Component guides](https://zenml.io/component-guide.txt) for integration details
  - [How-to guides](https://zenml.io/how-to-guides.txt) for practical implementations
  - [Complete documentation corpus](https://zenml.io/llms-full.txt) for comprehensive access

This structured approach helps AI tools better understand and utilize ZenML's documentation, enabling more accurate code suggestions and improved documentation search.

## 📜 License

ZenML is distributed under the terms of the Apache License Version 2.0.
A complete version of the license is available in the [LICENSE](LICENSE) file in
this repository. Any contribution made to this project will be licensed under
the Apache License Version 2.0.

<div>
<p align="left">
    <div align="left">
      Join our <a href="https://zenml.io/slack" target="_blank">
      <img width="18" src="https://cdn3.iconfinder.com/data/icons/logos-and-brands-adobe/512/306_Slack-512.png" alt="Slack"/>
    <b>Slack Community</b> </a> and be part of the ZenML family.
    </div>
    <br />
    <a href="https://zenml.io/features">Features</a>
    ·
    <a href="https://zenml.io/roadmap">Roadmap</a>
    ·
    <a href="https://github.com/zenml-io/zenml/issues">Report Bug</a>
    ·
    <a href="https://zenml.io/pro">Sign up for ZenML Pro</a>
    ·
    <a href="https://www.zenml.io/blog">Read Blog</a>
    ·
    <a href="https://github.com/issues?q=is%3Aopen+is%3Aissue+archived%3Afalse+user%3Azenml-io+label%3A%22good+first+issue%22">Contribute to Open Source</a>
    ·
    <a href="https://github.com/zenml-io/zenml-projects">Projects Showcase</a>
    <br />
    <br />
    🎉 Version 0.83.0 is out. Check out the release notes
    <a href="https://github.com/zenml-io/zenml/releases">here</a>.
    <br />
    🖥️ Download our VS Code Extension <a href="https://marketplace.visualstudio.com/items?itemName=ZenML.zenml-vscode">here</a>.
    <br />
  </p>
</div>
