---
description: Run your ML pipelines on Kubeflow Pipelines.
---

# Kubeflow

The ZenML Kubeflow Orchestrator allows you to run your ML pipelines on Kubeflow Pipelines without writing Kubeflow code. 

## Prerequisites

To use the Kubeflow Orchestrator, you'll need:

- ZenML `kubeflow` integration installed (`zenml integration install kubeflow`)
- Docker installed and running
- `kubectl` installed (optional, see below)
- A Kubernetes cluster with Kubeflow Pipelines installed (see deployment guide for your cloud provider)
- A remote artifact store and container registry in your ZenML stack
- A remote ZenML server deployed to the cloud
- The name of your Kubernetes context pointing to the remote cluster (optional, see below)

## Configuring the Orchestrator

There are two ways to configure the orchestrator:

1. Using a [Service Connector](../../how-to/auth-management/service-connectors-guide.md) to connect to the remote cluster (recommended for cloud-managed clusters). No local `kubectl` context needed.

```bash
zenml orchestrator register <ORCHESTRATOR_NAME> --flavor kubeflow
zenml service-connector list-resources --resource-type kubernetes-cluster -e  
zenml orchestrator connect <ORCHESTRATOR_NAME> --connector <CONNECTOR_NAME>
zenml stack update -o <ORCHESTRATOR_NAME>
```

2. Configuring `kubectl` with a context pointing to the remote cluster and setting `kubernetes_context` in the orchestrator config:

```bash  
zenml orchestrator register <ORCHESTRATOR_NAME> \
    --flavor=kubeflow \
    --kubernetes_context=<KUBERNETES_CONTEXT>
    
zenml stack update -o <ORCHESTRATOR_NAME>
```

## Running a Pipeline

Once configured, you can run any ZenML pipeline using the Kubeflow Orchestrator:

```python
python your_pipeline.py
```

This will create a Kubernetes pod for each step in your pipeline. You can view pipeline runs in the Kubeflow UI.

## Additional Configuration

You can further configure the orchestrator using `KubeflowOrchestratorSettings`:

```python
from zenml.integrations.kubeflow.flavors.kubeflow_orchestrator_flavor import KubeflowOrchestratorSettings

kubeflow_settings = KubeflowOrchestratorSettings(
   client_args={},  
   user_namespace="my_namespace",
   pod_settings={
       "affinity": {...},
       "tolerations": [...]
   }
)

@pipeline(
   settings={
       "orchestrator": kubeflow_settings
   }
)
```

This allows specifying client arguments, user namespace, pod affinity/tolerations, and more.

## Multi-Tenancy Deployments

For multi-tenant Kubeflow deployments, specify the `kubeflow_hostname` ending in `/pipeline` when registering the orchestrator:

```bash
zenml orchestrator register <NAME> \
   --flavor=kubeflow \
   --kubeflow_hostname=<KUBEFLOW_HOSTNAME> # e.g. https://mykubeflow.example.com/pipeline
```

And provide the namespace, username and password in the orchestrator settings:

```python
kubeflow_settings = KubeflowOrchestratorSettings(
   client_username="admin",
   client_password="abc123", 
   user_namespace="namespace_name"
)

@pipeline(
   settings={
       "orchestrator": kubeflow_settings
   }
)
```

For more advanced options and details, refer to the [full Kubeflow Orchestrator documentation](../../component-guide/orchestrators/kubeflow.md).

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


