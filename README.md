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

## 🎯 The Hidden Complexity of Production AI

You've built a great POC with LangGraph. Your RAG demo works perfectly. But now you need to:

- **Run evaluation pipelines** on every update
- **Process documents in batch** workflows
- **Track costs** across 5 different LLM providers
- **Prove compliance** for EU AI Act requirements
- **Unify observability** across LangFuse, LiteLLM, and other custom tools

**ZenML is the orchestration layer that connects it all** - without replacing
any of your existing tools.

## 👥 Who Should Use ZenML?

**Perfect for:**
- Platform teams drowning in LLM tool sprawl
- Enterprises running batch agent workflows (document processing, evals)
- Teams facing regulatory requirements (EU AI Act, healthcare, finance),
  especially those in high-risk categories (e.g. healthcare, finance)
- Organizations that need self-hosted/hybrid solutions with vendor support

**Not for:**
- Real-time agent serving (we currently work best with batch/scheduled workflows)
- Replacing your agent framework (we orchestrate, not execute)
- Generic CI/CD (we're purpose-built for AI/ML)

## What does ZenML add to your stack?

### Stack-agnostic: keep your code the same

- write your code once, run it anywhere
- build around your application logic, not around your infrastructure

### Built for platform teams

- don’t build your own platform, just use zenml
- we handle all the boring stuff, you just focus on what adds value
- we've built zenml based on the needs of our customers, so you can benefit from
  the collective experience of the community

### We track and version everything

- prompts, artifacts (input and output of any steps in a zenml pipeline),
  models, metadata, config and parameters used to invoke or trigger a pipeline,
  github SHA, logs, visualizations and any extra custom metadata you want to
  track like cost, latency etc.
- this all happens automatically
- (you'll need this for EU AI Act compliance)
- access everything programmatically via the ZenML SDK (or chat with your data using the ZenML MCP server)

### Supports MLOps as well as LLMOps

- ZenML has been around for a while so we're battle-tested in the MLOps space
- we've grown and built features around the LLMOps space too as this has slowly
  become more of a thing.
- super solid for MLOps, and this is a great foundation for LLMOps
- strong overlap between the needs of the two and many of our customers started
  out with MLOps and have now added or incorporated LLMOps into their workflows.

## Features

### Manage tool sprawl: Don't Replace - Supercharge

- One dashboard to rule them all.
- Keep using the same tools you know and love, but let ZenML give you more control and observability.
- Integrate with your favourite frameworks and libraries—ZenML sits on top, providing a unified view across your stack.
- Centralise experiment tracking, model registry, and pipeline orchestration without forcing you to migrate or refactor your existing workflows.
- Gain visibility into every step, from data ingestion to deployment, with detailed lineage and audit trails.
- Reduce context switching and manual handoffs by connecting disparate tools and teams through a single platform.

### Supports common use cases and workflows

- Traditional ML pipelines
- RAG pipelines
- Batch agentic workflows
- Agent deployment
- Evaluation pipelines
- EU AI Act compliance

### 🏗️ A Bridge Between Data Science and Platform Teams

**For Data Scientists**: Visual dashboards, one-click deployments, no YAML files
**For Platform Teams**: RBAC / access controls, audit logs, self-hosted, custom integrations


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
