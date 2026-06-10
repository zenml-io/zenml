---
description: Build production ML pipelines and durable AI agents with ZenML and Kitaru.
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

ZenML is a unified MLOps framework that extends the battle-tested principles you rely on for classical ML to the new world of AI agents. It's one place to develop, evaluate, and deploy your entire AI portfolio - from decision trees to complex multi-agent systems. By providing a single framework for your entire AI stack, ZenML enables developers across your organization to collaborate more effectively without maintaining separate toolchains for models and agents.

That story has two open-source projects behind it:

* **ZenML** is the MLOps framework: portable, production-ready **pipelines** for ML and LLM workloads, with versioned artifacts, caching, and infrastructure abstracted behind [stacks](https://docs.zenml.io/stacks).
* **[Kitaru](https://docs.zenml.io/kitaru)** is the durable execution layer for **AI agents**: it makes agent workflows persistent, replayable, and observable with a handful of primitives (`flow`, `checkpoint`, `wait`) instead of a graph DSL.

Each works on its own. You can run ZenML and never touch Kitaru, or pick up Kitaru purely to make one agent durable. If you do use both, they compose rather than coexist: a Kitaru flow is a dynamic ZenML pipeline under the hood, so your agents and pipelines run on the same stacks, persist artifacts to the same stores, and show up in the same server and dashboard.

### What are you building?

Pick the path that matches your work. Neither path requires the other, and adopting the second one later doesn't mean starting over.

<table data-view="cards"><thead><tr><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td><strong>ML Pipelines → ZenML</strong></td><td>Build, version, and deploy classical ML and LLM pipelines. Start with Hello World below, then the Starter guide.</td><td><a href="getting-started/hello-world.md">hello-world.md</a></td></tr><tr><td><strong>AI Agents → Kitaru</strong></td><td>Make agent workflows durable, replayable, and observable. Start with the Kitaru quickstart, then the Agents guide.</td><td><a href="https://docs.zenml.io/kitaru/getting-started/quickstart">Kitaru quickstart</a></td></tr></tbody></table>

### How these docs are organized

The documentation is split into spaces — the tabs at the top of this page. Knowing what lives where saves you a lot of searching:

| Space | What you'll find there |
| --- | --- |
| **ZenML** (you are here) | The pipelines framework: installation, core concepts, deployment, and how-to guides |
| **[Kitaru](https://docs.zenml.io/kitaru)** | The agents layer: quickstart, flows and checkpoints, framework adapters, and agent guides |
| **[Learn](https://docs.zenml.io/user-guides)** | Narrative guides for both projects: Starter, Production, LLMOps, and Agents tracks, plus tutorials and best practices |
| **[Stacks](https://docs.zenml.io/stacks)** | The infrastructure components — orchestrators, artifact stores, and more — that both pipelines and agents run on |
| **[SDK reference](https://docs.zenml.io/sdk-reference)** / **[API reference](https://docs.zenml.io/api-reference)** | Client and REST API references, organized per project |

### Getting Started

Set up ZenML and build your first pipeline:

<table data-view="cards"><thead><tr><th></th><th></th><th data-hidden data-card-cover data-type="files"></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td><strong>Installation</strong></td><td>Set up ZenML in your environment</td><td><a href=".gitbook/assets/production.png">production.png</a></td><td><a href="getting-started/installation.md">installation.md</a></td></tr><tr><td><strong>Core Concepts</strong></td><td>Understand ZenML fundamentals — and where Kitaru fits</td><td><a href=".gitbook/assets/core-concepts.png">core-concepts.png</a></td><td><a href="getting-started/core-concepts.md">core-concepts.md</a></td></tr><tr><td><strong>Hello World</strong></td><td>Build your first ML workflow</td><td><a href=".gitbook/assets/how-to.png">how-to.png</a></td><td><a href="getting-started/hello-world.md">hello-world.md</a></td></tr></tbody></table>

Building agents instead? The equivalent path lives in the Kitaru docs: [installation](https://docs.zenml.io/kitaru/getting-started/installation), [quickstart](https://docs.zenml.io/kitaru/getting-started/quickstart), and [core concepts](https://docs.zenml.io/kitaru/concepts).

If you use AI coding tools, see [LLM tooling](reference/llms-txt.md) for ZenML's MCP server and Agent Skills (including `zenml-scoping` and `zenml-pipeline-authoring`).

### Guides

<table data-view="cards"><thead><tr><th></th><th></th><th data-hidden data-card-cover data-type="files"></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td><strong>Starter Guide</strong></td><td>Get started with ZenML fundamentals and set up your first pipeline</td><td><a href=".gitbook/assets/starter.png">starter.png</a></td><td><a href="https://docs.zenml.io/user-guides/starter-guide">Starter guide</a></td></tr><tr><td><strong>Production Guide</strong></td><td>Move your ML pipelines from development to production</td><td><a href=".gitbook/assets/prod.png">prod.png</a></td><td><a href="https://docs.zenml.io/user-guides/production-guide">Production guide</a></td></tr><tr><td><strong>LLMOps Guide</strong></td><td>Build and deploy Large Language Model pipelines</td><td><a href=".gitbook/assets/llm.png">llm.png</a></td><td><a href="https://docs.zenml.io/user-guides/llmops-guide">LLMOps guide</a></td></tr><tr><td><strong>Agents Guide</strong></td><td>Build durable AI agents and an internal agent platform with Kitaru</td><td><a href=".gitbook/assets/llm.png">llm.png</a></td><td><a href="https://docs.zenml.io/user-guides/agents-guide">Agents guide</a></td></tr></tbody></table>

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
