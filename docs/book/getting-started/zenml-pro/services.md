---
description: Understanding ZenML Pro services and how data flows through pipelines.
icon: server
---

# Services Overview

ZenML Pro's architecture consists of key services that work together to execute, track, and manage your ML pipelines. Understanding these services helps you make informed decisions about deployment, security, and infrastructure.

## Core Services

ZenML Pro has three main services, each with distinct responsibilities:

| Service | Purpose | Deployment Location |
|---------|---------|---------------------|
| [**Workspace Server**](workspace-server.md) | Stores metadata, serves APIs, manages entities | Your infrastructure (Hybrid/Self-hosted) or ZenML (SaaS) |
| [**Control Plane**](control-plane.md) | Authentication, RBAC, organization management | ZenML infrastructure (SaaS/Hybrid) or yours (Self-hosted) |
| [**Workload Manager**](workload-managers.md) | Executes pipelines from UI, manages runner pods | Your infrastructure |

## Pipeline Execution Data Flow (remote docker runtime)

When you execute a pipeline, data flows through the system in a well-defined sequence:

**1. Code Execution**

You write code and run pipelines with your client SDK using Python. The pipeline definition specifies the steps and their dependencies.

**2. Token Acquisition**

The ZenML client fetches credentials from your ZenML workspace for:
- Pushing Docker images to the selected container registry
- Communicating with the selected artifact store
- Submitting workloads to your orchestrator

{% hint style="info" %}
Your local Python environment needs the client libraries for your stack components (e.g., `boto3` for AWS, `google-cloud-storage` for GCP).
{% endhint %}

**3. Image & Workload Submission**

The client builds and pushes Docker images to your container registry, then submits the workload to your orchestrator. If you have a code repository configured, code can be pulled directly instead of being baked into the image.

**4. Orchestrator Execution**

In the orchestrator environment:
- The Docker image is pulled from your container registry
- The necessary code is pulled in from the artifact store/code repo
- A connection to your ZenML workspace is established
- The relevant pipeline/step code is executed

**5. Runtime Data Flow**

During execution:
- **Pipeline and step run metadata** is logged to your ZenML workspace
- **Logs** are streamed to your log backend
- **Artifacts** are written to your artifact store
- **Metadata** pointing to these artifacts is persisted

**6. Observability**

The ZenML Dashboard connects to your workspace and uses all persisted metadata to provide a complete observability plane for monitoring, debugging, and analyzing your ML workflows.

## Where Data Lives

Understanding where different types of data reside is crucial for security and compliance:

| Data Type | Description | Location |
|-----------|-------------|----------|
| **Pipeline Metadata** | Run status, step execution details, artifact pointers | Workspace Server database |
| **Artifacts** | Model weights, datasets, evaluation results | Your artifact store (S3, GCS, etc.) |
| **Container Images** | Docker images with your code and dependencies | Your container registry |
| **Logs** | Execution logs from pipeline runs | Your configured log backend |
| **Secrets** | Credentials and sensitive configuration | ZenML secrets store or external vault |
| **User/Org Data** | Authentication, RBAC, organization settings | Control Plane database |

{% hint style="success" %}
In all ZenML deployment scenarios, your actual ML data (models, datasets, artifacts) stays in your infrastructure. Only metadata flows to the ZenML services.
{% endhint %}

## Service Deep Dives

For detailed information on each service including responsibilities, required permissions, and network requirements:

<table data-view="cards"><thead><tr><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td><strong>Workspace Server</strong></td><td>Metadata storage, API serving, entity management, token provisioning</td><td><a href="workspace-server.md">workspace-server.md</a></td></tr><tr><td><strong>Control Plane</strong></td><td>Authentication, RBAC, organization management, workspace provisioning</td><td><a href="control-plane.md">control-plane.md</a></td></tr><tr><td><strong>Workload Manager</strong></td><td>UI-triggered pipeline execution, runner pod management</td><td><a href="workload-managers.md">workload-managers.md</a></td></tr></tbody></table>

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>

