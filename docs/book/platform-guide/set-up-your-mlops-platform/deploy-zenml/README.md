---
description: A guide on how to deploy ZenML
---

# Deploy ZenML

### The components of a ZenML Deployment

A ZenML deployment typically consist of the following components:

* A FastAPI HTTP server that exposes a RESTful API
  * your local machine connects to this server to read and write the stack configurations to allow collaboration.
  * the individual orchestrators and step operators communicate with the server to write and track your pipeline run data.
  * the dashboard is served from the server to give a UI interface to all of your metadata.
* An SQL database as the backend to track configurations and metadata.
  * For production currently only MySQL is supported
* An optional external secrets management service that is used as a backend for the ZenML secrets store.

You can use any of the following ways to get started:

<table data-view="cards"><thead><tr><th></th><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td></td><td></td><td></td><td><a href="deployment-using-the-cli.md">deployment-using-the-cli.md</a></td></tr><tr><td></td><td></td><td></td><td></td></tr><tr><td></td><td></td><td></td><td></td></tr></tbody></table>

* The [`zenml deploy` CLI command](cli.md) that provides an easy interface to deploy on Kubernetes in AWS, GCP or Azure.
* A [Docker image](docker.md) that you can run in any environment of your choice.
* A [Helm chart](helm.md) that can be deployed to any Kubernetes cluster (on-prem or managed).

In the following pages, we take a look at each of those options.
