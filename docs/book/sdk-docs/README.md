---
description: Reference hub for the ZenML and Kitaru SDKs and CLIs.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Overview

ZenML and Kitaru each provide SDKs for working with their APIs:

* **ZenML** provides a Python SDK and CLI for building, managing, and deploying production-ready ML pipelines.
* **Kitaru** provides Python and TypeScript SDKs for recording, replaying, and improving AI agents. Its CLI ships with the Python package.

## ZenML SDK

The ZenML SDK provides Python tools and interfaces for building, managing, and deploying production-ready machine learning pipelines. This documentation helps you get the most out of ZenML's features.

<table data-card-size="large" data-view="cards" data-full-width="false"><thead><tr><th></th><th></th><th data-hidden data-card-cover data-type="files"></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td><strong>SDK Documentation</strong></td><td>Complete API documentation for all ZenML modules, classes, and functions.</td><td><a href=".gitbook/assets/sdk.png">sdk.png</a></td><td><a href="https://sdkdocs.zenml.io">https://sdkdocs.zenml.io</a></td></tr><tr><td><strong>CLI Methods</strong></td><td>Command-line tools for managing ZenML pipelines, stacks, and deployments.</td><td><a href=".gitbook/assets/cli.png">cli.png</a></td><td><a href="https://sdkdocs.zenml.io/latest/cli.html">https://sdkdocs.zenml.io/latest/cli.html</a></td></tr><tr><td><strong>ZenML Client</strong></td><td>Python client for interacting with ZenML projects, repositories, and services.</td><td><a href=".gitbook/assets/client.png">client.png</a></td><td><a href="https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html">https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html</a></td></tr><tr><td><strong>Integrations</strong></td><td>Connect ZenML with popular ML tools, orchestrators, and cloud services.</td><td><a href=".gitbook/assets/integrations.png">integrations.png</a></td><td><a href="https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-airflow.html">https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-airflow.html</a></td></tr></tbody></table>

## Kitaru SDK

[Kitaru](https://docs.zenml.io/kitaru) is ZenML's sibling project for recording, replaying, and improving AI agents: traces you can run, not just read. Its Python and TypeScript SDKs talk to the same Kitaru server over the same REST API. Framework adapters support [Python and TypeScript agents](https://docs.zenml.io/kitaru/adapters/adapters). The generated Python SDK and CLI reference is published on a dedicated site.

<table data-card-size="large" data-view="cards" data-full-width="false"><thead><tr><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td><strong>Python SDK &#x26; CLI Reference</strong></td><td>Complete generated API reference for the Kitaru Python SDK and command-line interface.</td><td><a href="https://sdkdocs.kitaru.ai">https://sdkdocs.kitaru.ai</a></td></tr><tr><td><strong>Python &#x26; TypeScript SDK Guide</strong></td><td>How both SDKs connect, authenticate, expose resources, and hand work to Kitaru workers.</td><td><a href="https://docs.zenml.io/kitaru/get-help/sdks">https://docs.zenml.io/kitaru/get-help/sdks</a></td></tr><tr><td><strong>Python Client</strong></td><td>Programmatic interface to a Kitaru server: sessions, replays, evaluators, cohorts, and experiments.</td><td><a href="kitaru/client.md">kitaru/client.md</a></td></tr></tbody></table>

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
