---
description: A guide on how to deploy ZenML in a self-hosted environment.
---

# 🔧 ZenML Self-Hosted

A ZenML deployment typically looks like this:

<figure><img src="https://github.com/zenml-io/zenml/blob/release/0.45.4/docs/.gitbook/assets/SystemArchitectureZenMLDeployment.png" alt=""><figcaption></figcaption></figure>

Some of the important components at play include:

* An **HTTP server** that exposes a RESTful API
  * the client's machine connects to this server to read and write the stack configurations to allow collaboration
  * the individual orchestrators and step operators communicate with the server to write and track the pipeline run data
  * the dashboard is served from the server to give a UI interface to all the metadata
* An **SQL database** that acts as the backend to track configurations and metadata
  * for production, currently, only MySQL is supported
* An optional **secrets management service** that is used as a backend for the ZenML secrets store

Choose the most appropriate deployment strategy for you out of the following options to get started with the deployment:

<table data-card-size="large" data-view="cards"><thead><tr><th></th><th></th><th data-hidden></th><th data-hidden data-type="content-ref"></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td><mark style="color:purple;"><strong>Deploy with ZenML CLI</strong></mark></td><td>Deploying ZenML on cloud using the ZenML CLI.</td><td></td><td></td><td><a href="deploy-with-zenml-cli.md">deploy-with-zenml-cli.md</a></td></tr><tr><td><mark style="color:purple;"><strong>Deploy with Docker</strong></mark></td><td>Deploying ZenML in a Docker container.</td><td></td><td></td><td><a href="deploy-with-docker.md">deploy-with-docker.md</a></td></tr><tr><td><mark style="color:purple;"><strong>Deploy with Helm</strong></mark></td><td>Deploying ZenML in a Kubernetes cluster with Helm.</td><td></td><td></td><td><a href="deploy-with-helm.md">deploy-with-helm.md</a></td></tr><tr><td><mark style="color:purple;"><strong>Deploy using HuggingFace Spaces</strong></mark></td><td>Deploying ZenML to Huggingface Spaces.</td><td></td><td></td><td><a href="deploy-using-huggingface-spaces.md">deploy-using-huggingface-spaces.md</a></td></tr></tbody></table>

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
