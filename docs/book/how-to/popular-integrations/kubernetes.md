---
description: Learn how to deploy ZenML pipelines on a Kubernetes cluster.
---

# Kubernetes

The ZenML Kubernetes Orchestrator allows you to run your ML pipelines on a Kubernetes cluster without writing Kubernetes code. It's a lightweight alternative to more complex orchestrators like Airflow or Kubeflow.

## Prerequisites

To use the Kubernetes Orchestrator, you'll need:

- ZenML `kubernetes` integration installed (`zenml integration install kubernetes`)
- Docker installed and running
- `kubectl` installed
- A remote artifact store and container registry in your ZenML stack
- A deployed Kubernetes cluster
- A configured `kubectl` context pointing to the cluster (optional, see below)

## Deploying the Orchestrator

You can deploy the orchestrator from the ZenML CLI:

```bash
zenml orchestrator deploy k8s_orchestrator --flavor=kubernetes --provider=<YOUR_PROVIDER>
```

## Configuring the Orchestrator

There are two ways to configure the orchestrator:

1. Using a [Service Connector](../../how-to/auth-management/service-connectors-guide.md) to connect to the remote cluster. This is the recommended approach, especially for cloud-managed clusters. No local `kubectl` context is needed.

```bash
zenml orchestrator register <ORCHESTRATOR_NAME> --flavor kubernetes
zenml service-connector list-resources --resource-type kubernetes-cluster -e
zenml orchestrator connect <ORCHESTRATOR_NAME> --connector <CONNECTOR_NAME>
zenml stack register <STACK_NAME> -o <ORCHESTRATOR_NAME> ... --set
```

2. Configuring `kubectl` with a context pointing to the remote cluster and setting the `kubernetes_context` in the orchestrator config:

```bash
zenml orchestrator register <ORCHESTRATOR_NAME> \
    --flavor=kubernetes \
    --kubernetes_context=<KUBERNETES_CONTEXT>

zenml stack register <STACK_NAME> -o <ORCHESTRATOR_NAME> ... --set
```

## Running a Pipeline

Once configured, you can run any ZenML pipeline using the Kubernetes Orchestrator:

```bash
python your_pipeline.py
```

This will create a Kubernetes pod for each step in your pipeline. You can interact with the pods using `kubectl` commands.

For more advanced configuration options and additional details, refer to the [full Kubernetes Orchestrator documentation](../../component-guide/orchestrators/kubernetes.md).

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


