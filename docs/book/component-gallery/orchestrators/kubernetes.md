---
description: How to orchestrate pipelines with Kubernetes
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The Kubernetes orchestrator is an [orchestrator](./orchestrators.md) flavor 
provided with the ZenML `kubernetes` integration that runs your pipelines on a 
[Kubernetes](https://kubernetes.io/) cluster.

{% hint style="warning" %}
This component is only meant to be used within the context of [remote ZenML deployment scenario](../../getting-started/deploying-zenml/deploying-zenml.md). Usage with a local ZenML deployment may lead to unexpected behavior!
{% endhint %}

## When to use it

You should use the Kubernetes orchestrator if:
* you're looking lightweight way of running your pipelines on Kubernetes.
* you don't need a UI to list all your pipelines runs.
* you're not willing to maintain [Kubeflow Pipelines](./kubeflow.md)
on your Kubernetes cluster.
* you're not interested in paying for managed solutions like [Vertex](./vertex.md).

## How to deploy it

The Kubernetes orchestrator requires a Kubernetes cluster in order to run.
There are many ways to deploy a Kubernetes cluster using different cloud providers
or on your custom infrastructure, and we can't possibly cover all of them, 
but you can check out our cloud guide 

If the above Kubernetes cluster is deployed remotely on the cloud, then another
pre-requisite to use this orchestrator would be to deploy and connect to a
[remote ZenML server](../../getting-started/deploying-zenml/deploying-zenml.md).

### Infrastructure Deployment

A Kubernetes orchestrator can be deployed directly from the ZenML CLI:

```shell
zenml orchestrator deploy k8s_orchestrator --flavor=kubernetes ...
```

You can pass other configuration specific to the stack components as key-value
arguments. If you don't provide a name, a random one is generated for you. For
more information about how to work use the CLI for this, please refer to [the
dedicated documentation
section](../../advanced-guide/practical/stack-recipes.md#deploying-stack-components-directly).

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
zenml orchestrator register <ORCHESTRATOR_NAME> \
    --flavor=kubernetes \
    --kubernetes_context=<KUBERNETES_CONTEXT>

# Register and activate a stack with the new orchestrator
zenml stack register <STACK_NAME> -o <ORCHESTRATOR_NAME> ... --set
```

{% hint style="info" %}
ZenML will build a Docker image called `<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>`
which includes your code and use it to run your pipeline steps in Kubernetes. 
Check out [this page](../../starter-guide/production-fundamentals/containerization.md)
if you want to learn more about how ZenML builds these images and
how you can customize them.
{% endhint %}

You can now run any ZenML pipeline using the Kubernetes orchestrator:
```shell
python file_that_runs_a_zenml_pipeline.py
```

### Additional configuration

For additional configuration of the Kubernetes orchestrator, you can pass
`KubernetesOrchestratorSettings` which allows you to configure (among others) the following attributes:

* `pod_settings`: Node selectors, affinity and tolerations to apply to the Kubernetes Pods running
your pipeline. These can be either specified using the Kubernetes model objects or as dictionaries.

```python
from zenml.integrations.kubernetes.flavors.kubernetes_orchestrator_flavor import KubernetesOrchestratorSettings
from kubernetes.client.models import V1Toleration


kubernetes_settings = KubernetesOrchestratorSettings(
    pod_settings={
        "affinity": {
            "nodeAffinity": {
                "requiredDuringSchedulingIgnoredDuringExecution": {
                    "nodeSelectorTerms": [
                        {
                            "matchExpressions": [
                                {
                                    "key": "node.kubernetes.io/name",
                                    "operator": "In",
                                    "values": ["my_powerful_node_group"],
                                }
                            ]
                        }
                    ]
                }
            }
        },
        "tolerations": [
            V1Toleration(
                key="node.kubernetes.io/name",
                operator="Equal",
                value="",
                effect="NoSchedule"
            )
        ]
    }
)

@pipeline(
    settings={
        "orchestrator.kubernetes": kubernetes_settings
    }
)
  ...
```

Check out the
[API docs](https://apidocs.zenml.io/latest/integration_code_docs/integrations-kubernetes/#zenml.integrations.kubernetes.flavors.kubernetes_orchestrator_flavor.KubernetesOrchestratorSettings)
for a full list of available attributes and [this docs page](../..//advanced-guide/pipelines/settings.md)
for more information on how to specify settings.

A concrete example of using the Kubernetes orchestrator can be found 
[here](https://github.com/zenml-io/zenml/tree/main/examples/kubernetes_orchestration).

For more information and a full list of configurable attributes of the 
Kubernetes orchestrator, check out the [API Docs](https://apidocs.zenml.io/latest/integration_code_docs/integrations-kubernetes/#zenml.integrations.kubernetes.orchestrators.kubernetes_orchestrator.KubernetesOrchestrator).

### Enabling CUDA for GPU-backed hardware

Note that if you wish to use this orchestrator to run steps on a GPU, you will
need to follow [the instructions on this page](../../advanced-guide/pipelines/gpu-hardware.md) to ensure that it works. It
requires adding some extra settings customization and is essential to enable
CUDA for the GPU to give its full acceleration.
