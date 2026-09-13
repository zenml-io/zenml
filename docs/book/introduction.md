---
description: Build production ML pipelines with ZenML and improve agentic systems with Kitaru.
icon: torii-gate
layout:
  title:
    visible: true
  description:
    visible: true
  tableOfContents:
    visible: true
  outline:
    visible: false
  pagination:
    visible: false
---

# Welcome to ZenML

ZenML is an open-source framework for orchestrating production ML and LLM pipelines, including pipelines that run agentic workloads.

That story has two open-source projects behind it:

* **ZenML** is the MLOps framework: portable, production-ready **pipelines** for ML and LLM workloads, with versioned artifacts, caching, and infrastructure abstracted behind [stacks](https://docs.zenml.io/stacks).
* **[Kitaru](https://docs.zenml.io/kitaru)** is for **evaluating and improving agentic systems**. It turns recorded or imported production traces into sessions for investigation, cohorts, evaluators, replay experiments, regression testing, and CI.

Each works on its own. ZenML orchestrates pipelines; Kitaru provides evals and improvement loops for agentic systems. Kitaru runs its own lightweight server, with workers that execute replays in your environment.

### What are you building?

Pick the path that matches your work. Neither path requires the other, and adopting the second one later doesn't mean starting over.

<table data-view="cards"><thead><tr><th></th><th></th><th data-hidden data-card-cover data-type="files"></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td><strong>ML Pipelines → ZenML</strong></td><td>Build, version, and deploy classical ML and LLM pipelines. Start with Hello World, then the Starter guide.</td><td><a href=".gitbook/assets/how-to.png">how-to.png</a></td><td><a href="getting-started/hello-world.md">hello-world.md</a></td></tr><tr><td><strong>Agent evals → Kitaru</strong></td><td>Investigate production traces, define evaluators and cohorts, and test changes through replay experiments. Start with the Kitaru quickstart.</td><td><a href=".gitbook/assets/llm.png">llm.png</a></td><td><a href="https://docs.zenml.io/kitaru/getting-started/quickstart">Kitaru quickstart</a></td></tr></tbody></table>

### How these docs are organized

The documentation is split into spaces — the tabs at the top of this page. Knowing what lives where saves you a lot of searching:

| Space | What you'll find there |
| --- | --- |
| **ZenML** (you are here) | The pipelines framework: installation, core concepts, deployment, and how-to guides |
| **[Kitaru](https://docs.zenml.io/kitaru)** | Agent evals and improvement loops: production sessions, investigations, cohorts, evaluators, replay experiments, and regression testing |
| **[Learn](https://docs.zenml.io/user-guides)** | Narrative ZenML guides: Starter, Production, and LLMOps, plus tutorials and best practices |
| **[Stacks](https://docs.zenml.io/stacks)** | The infrastructure components — orchestrators, artifact stores, and more — that ZenML pipelines run on |
| **[SDK reference](https://docs.zenml.io/sdk-reference)** / **[API reference](https://docs.zenml.io/api-reference)** | Client and REST API references, organized per project |
| **[Changelog](https://docs.zenml.io/changelog)** | Release notes, version by version |

### First steps

Whichever path you picked, the first steps are the same shape: install, run something real, then learn the concepts.

| | ML Pipelines (ZenML) | Agent Evals (Kitaru) |
| --- | --- | --- |
| **Install** | [Installation](getting-started/installation.md) | [Installation](https://docs.zenml.io/kitaru/getting-started/installation) |
| **First run** | [Hello World](getting-started/hello-world.md) | [Quickstart](https://docs.zenml.io/kitaru/getting-started/quickstart) |
| **Concepts** | [Core Concepts](getting-started/core-concepts.md) | [Core Concepts](https://docs.zenml.io/kitaru/concepts) |

If you use AI coding tools, see [LLM tooling](reference/llms-txt.md) for ZenML's MCP server and Agent Skills (including `zenml-scoping` and `zenml-pipeline-authoring`).

### Guides

<table data-view="cards"><thead><tr><th></th><th></th><th data-hidden data-card-cover data-type="files"></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td><strong>Starter Guide</strong></td><td>Get started with ZenML fundamentals and set up your first pipeline</td><td><a href=".gitbook/assets/starter.png">starter.png</a></td><td><a href="https://docs.zenml.io/user-guides/starter-guide">Starter guide</a></td></tr><tr><td><strong>Production Guide</strong></td><td>Move your ML pipelines from development to production</td><td><a href=".gitbook/assets/prod.png">prod.png</a></td><td><a href="https://docs.zenml.io/user-guides/production-guide">Production guide</a></td></tr><tr><td><strong>Kitaru</strong></td><td>Replay a real run with one change, and improve agents across a cohort of real runs</td><td><a href=".gitbook/assets/llm.png">llm.png</a></td><td><a href="https://docs.zenml.io/kitaru">Kitaru docs</a></td></tr></tbody></table>

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
