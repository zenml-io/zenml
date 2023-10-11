---
description: How to orchestrate pipelines with Kubernetes
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The Kubernetes orchestrator is an [orchestrator](./orchestrators.md) flavor 
provided with the ZenML `kubernetes` integration that runs your pipelines on a 
[Kubernetes](https://kubernetes.io/) cluster.

## When to use it

You should use the Kubernetes orchestrator if:
* you're looking lightweight way of running your pipelines on Kubernetes.
* you don't need a UI to list all your pipelines runs.
* you're not willing to maintain [Kubeflow Pipelines](./kubeflow.md)
on your Kubernetes cluster.
* you're not interested in paying for managed solutions like [Vertex](./gcloud-vertexai.md).

## How to deploy it

The Kubernetes orchestrator requires a Kubernetes cluster in order to run.
There are many ways to deploy a Kubernetes cluster using different cloud providers
or on your custom infrastructure, and we can't possibly cover all of them, 
but you can check out our cloud guide [ZenML Cloud Guide](../../stack-deployment-guide/overview.md)
for some complete stack deployments which use the Kubernetes orchestrator.

## How to use it

To use the Kubernetes orchestrator, we need:
* The ZenML `kubernetes` integration installed. If you haven't done so, run 
    ```shell
    zenml integration install kubernetes
    ```
* [Docker](https://www.docker.com) installed and running.
* [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl) installed.
* A [remote artifact store](../artifact-stores/artifact-stores.md) as part of 
your stack.
* A [remote container registry](../container-registries/container-registries.md) 
as part of your stack.
* A Kubernetes cluster [deployed](#how-to-deploy-it) and the name of your 
Kubernetes context which points to this cluster. Run`kubectl config get-contexts` 
to see a list of available contexts.

We can then register the orchestrator and use it in our active stack:
```shell
zenml orchestrator register <NAME> \
    --flavor=kubernetes \
    --kubernetes_context=<KUBERNETES_CONTEXT>

# Add the orchestrator to the active stack
zenml stack update -o <NAME>
```

{% hint style="info" %}
ZenML will build a Docker image called `<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>`
which includes your code and use it to run your pipeline steps in Kubernetes. 
Check out [this page](../../advanced-guide/pipelines/containerization.md)
if you want to learn more about how ZenML builds these images and
how you can customize them.
{% endhint %}

You can now run any ZenML pipeline using the Kubernetes orchestrator:
```shell
python file_that_runs_a_zenml_pipeline.py
```

A concrete example of using the Kubernetes orchestrator can be found 
[here](https://github.com/zenml-io/zenml/tree/main/examples/kubernetes_orchestration).

For more information and a full list of configurable attributes of the 
Kubernetes orchestrator, check out the [API Docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.kubernetes.orchestrators.kubernetes_orchestrator.KubernetesOrchestrator).