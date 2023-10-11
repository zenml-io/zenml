---
description: How to orchestrate pipelines with Kubeflow
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The Kubeflow orchestrator is an [orchestrator](./orchestrators.md) flavor 
provided with the ZenML `kubeflow` integration that uses [Kubeflow Pipelines](https://www.kubeflow.org/docs/components/pipelines/introduction/)
to run your pipelines.

{% hint style="warning" %}
This component is only meant to be used within the context of [remote ZenML deployment scenario](../../getting-started/deploying-zenml/deploying-zenml.md). Usage with a local ZenML deployment may lead to unexpected behavior!
{% endhint %}

## When to use it

You should use the Kubeflow orchestrator if:
* you're looking for a proven production-grade orchestrator.
* you're looking for a UI in which you can track your pipeline runs.
* you're already using Kubernetes or are not afraid of setting up and 
maintaining a Kubernetes cluster.
* you're willing to deploy and maintain Kubeflow Pipelines on your cluster.

## How to deploy it

The Kubeflow orchestrator supports two different modes: `Local` and `remote`.
In case you want to run the orchestrator on a local Kubernetes cluster running
on your machine, there is no additional infrastructure setup necessary.

If you want to run your pipelines on a remote cluster instead, you'll need to
set up a Kubernetes cluster and deploy Kubeflow Pipelines:

{% tabs %}
{% tab title="AWS" %}

* Have an existing
  AWS [EKS cluster](https://docs.aws.amazon.com/eks/latest/userguide/create-cluster.html)
  set up.
* Make sure you have the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) set up.
* Download and [install](https://kubernetes.io/docs/tasks/tools/) `kubectl`
  and [configure](https://aws.amazon.com/premiumsupport/knowledge-center/eks-cluster-connection/)
  it to talk to your EKS cluster using the following command:

  ```powershell
  aws eks --region REGION update-kubeconfig --name CLUSTER_NAME
  ```
* [Install](https://www.kubeflow.org/docs/components/pipelines/installation/standalone-deployment/#deploying-kubeflow-pipelines)
  Kubeflow Pipelines onto your cluster.
  {% endtab %}

{% tab title="GCP" %}

* Have an existing
  GCP [GKE cluster](https://cloud.google.com/kubernetes-engine/docs/quickstart)
  set up.
* Make sure you have the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install-sdk) 
  set up first.
* Download and [install](https://kubernetes.io/docs/tasks/tools/) `kubectl`
  and [configure](https://cloud.google.com/kubernetes-engine/docs/how-to/cluster-access-for-kubectl)
  it to talk to your GKE cluster using the following command:

  ```powershell
  gcloud container clusters get-credentials CLUSTER_NAME
  ```
* [Install](https://www.kubeflow.org/docs/distributions/gke/deploy/overview/)
  Kubeflow Pipelines onto your cluster.
  {% endtab %}

{% tab title="Azure" %}

* Have an
  existing [AKS cluster](https://azure.microsoft.com/en-in/services/kubernetes-service/#documentation)
  set up.
* Make sure you have the [`az` CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) set up first.
* Download and [install](https://kubernetes.io/docs/tasks/tools/) `kubectl` and
  it to talk to your AKS cluster using the following command:

  ```powershell
  az aks get-credentials --resource-group RESOURCE_GROUP --name CLUSTER_NAME
  ```
* [Install](https://www.kubeflow.org/docs/components/pipelines/installation/standalone-deployment/#deploying-kubeflow-pipelines)
  Kubeflow Pipelines onto your cluster.

> Since Kubernetes v1.19, AKS has shifted
>
to [`containerd`](https://docs.microsoft.com/en-us/azure/aks/cluster-configuration#container-settings)
> . However, the workflow controller installed with the Kubeflow installation
> has `Docker` set as the default runtime. In order to make your pipelines work,
> you have to change the value to one of the options
>
listed [here](https://argoproj.github.io/argo-workflows/workflow-executors/#workflow-executors)
> , preferably `k8sapi`.&#x20;
>
> This change has to be made by editing the `containerRuntimeExecutor` property
> of the `ConfigMap` corresponding to the workflow controller. Run the following
> commands to first know what config map to change and then to edit it to
> reflect
> your new value.
>
> ```
> kubectl get configmap -n kubeflow
> kubectl edit configmap CONFIGMAP_NAME -n kubeflow
> # This opens up an editor that can be used to make the change.
> ```
{% endtab %}
{% endtabs %}

{% hint style="info" %}
If one or more of the deployments are not in the `Running` state, try increasing
the number of nodes in your cluster.
{% endhint %}

{% hint style="warning" %}
If you're installing Kubeflow Pipelines manually, make sure the Kubernetes 
service is called exactly `ml-pipeline`. This is a requirement for ZenML to 
connect to your Kubeflow Pipelines deployment.
{% endhint %}

## How to use it

To use the Kubeflow orchestrator, we need:
* The ZenML `kubeflow` integration installed. If you haven't done so, run 
    ```shell
    zenml integration install kubeflow
    ```
* [Docker](https://www.docker.com) installed and running.
* [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl) installed.

{% tabs %}
{% tab title="Local" %}

When using the Kubeflow orchestrator locally, you'll additionally need:
* [K3D](https://k3d.io/v5.2.1/#installation) installed to spin up a local 
Kubernetes cluster.
* A [local container registry](../container-registries/default.md) as part of 
your stack.

{% hint style="warning" %}
The local Kubeflow Pipelines deployment requires more than 2 GB of RAM,
so if you're using Docker Desktop make sure to update the resource
limits in the preferences.
{% endhint %}

We can then register the orchestrator and use it in our active stack:
```shell
zenml orchestrator register <ORCHESTRATOR_NAME> \
    --flavor=kubeflow

# Register and activate a stack with the new orchestrator
zenml stack register <STACK_NAME> -o <ORCHESTRATOR_NAME> ... --set
```

{% endtab %}

{% tab title="Remote" %}

When using the Kubeflow orchestrator with a remote cluster, you'll additionally 
need:
* A remote ZenML server deployed to the cloud. See the [deployment guide](../../getting-started/deploying-zenml/deploying-zenml.md) for more information.
* Kubeflow pipelines deployed on a remote cluster. See the [deployment section](#how-to-deploy-it) 
for more information.
* The name of your Kubernetes context which points to your remote cluster. 
Run `kubectl config get-contexts` to see a list of available contexts.
* A [remote artifact store](../artifact-stores/artifact-stores.md) as part of 
your stack.
* A [remote container registry](../container-registries/container-registries.md) 
as part of your stack.

We can then register the orchestrator and use it in our active stack:

```shell
zenml orchestrator register <NAME> \
    --flavor=kubeflow \
    --kubernetes_context=<KUBERNETES_CONTEXT>

# Add the orchestrator to the active stack
zenml stack update -o <NAME>
```

{% endtab %}
{% endtabs %}

{% hint style="info" %}
ZenML will build a Docker image called `<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>`
which includes your code and use it to run your pipeline steps in Kubeflow. 
Check out [this page](../../advanced-guide/pipelines/containerization.md)
if you want to learn more about how ZenML builds these images and how you can 
customize them.
{% endhint %}

Once the orchestrator is part of the active stack, we need to run
`zenml stack up` before running any pipelines. This command
* forwards a port, so you can view the Kubeflow UI in your browser.
* (in the local case) uses K3D to provision a Kubernetes cluster
on your machine and deploys Kubeflow Pipelines on it.

You can now run any ZenML pipeline using the Kubeflow orchestrator:
```shell
python file_that_runs_a_zenml_pipeline.py
```

### Additional configuration

For additional configuration of the Kubeflow orchestrator, you can pass
`KubeflowOrchestratorSettings` which allows you to configure (among others) the following attributes:

* `client_args`: Arguments to pass when initializing the KFP client.
* `user_namespace`: The user namespace to use when creating experiments and runs.
* `pod_settings`: Node selectors, affinity and tolerations to apply to the Kubernetes Pods running
your pipline. These can be either specified using the Kubernetes model objects or as dictionaries.

```python
from zenml.integrations.kubeflow.flavors.kubeflow_orchestrator_flavor import KubeflowOrchestratorSettings
from kubernetes.client.models import V1Toleration


kubeflow_settings = KubeflowOrchestratorSettings(
    client_args={},
    user_namespace="my_namespace",
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
        "orchestrator.kubeflow": kubeflow_settings
    }
)
    ...
```

Check out the
[API docs](https://apidocs.zenml.io/latest/integration_code_docs/integrations-kubeflow/#zenml.integrations.kubeflow.flavors.kubeflow_orchestrator_flavor.KubeflowOrchestratorSettings)
for a full list of available attributes and [this docs page](../..//advanced-guide/pipelines/settings.md)
for more information on how to specify settings.

### Enabling CUDA for GPU-backed hardware

Note that if you wish to use this orchestrator to run steps on a GPU, you will
need to follow [the instructions on this page](../../advanced-guide/pipelines/gpu-hardware.md) to ensure that it works. It
requires adding some extra settings customization and is essential to enable
CUDA for the GPU to give its full acceleration.


## Important Note for Multi-Tenancy Deployments

Kubeflow has a notion of [multi-tenancy](https://www.kubeflow.org/docs/components/multi-tenancy/overview/) 
built into its deployment. Kubeflow’s multi-user isolation simplifies user 
operations because each user only views and edited\s the Kubeflow components 
and model artifacts defined in their configuration.

Using the ZenML Kubeflow orchestrator on a multi-tenant deployment without any settings will result in the following error:

```shell
HTTP response body: {"error":"Invalid input error: Invalid resource references for experiment. ListExperiment requires filtering by namespace.","code":3,"message":"Invalid input error: Invalid resource references for experiment. ListExperiment requires filtering by 
namespace.","details":[{"@type":"type.googleapis.com/api.Error","error_message":"Invalid resource references for experiment. ListExperiment requires filtering by namespace.","error_details":"Invalid input error: Invalid resource references for experiment. ListExperiment requires filtering by namespace."}]}
```

In order to get it to work, we need to leverage the `KubeflowOrchestratorSettings` referenced above. By setting the namespace option, and by passing in the right authentication credentials to the Kubeflow Pipelines Client, we can make it work.

First, when registering your kubeflow orchestrator, please make sure to include the `kubeflow_hostname` parameter.
The `kubeflow_hostname` **must end with the `/pipeline` post-fix**.

```shell
zenml orchestrator register <NAME> \
    --flavor=kubeflow \
    --kubernetes_context=<KUBERNETES_CONTEXT> \  
    --kubeflow_hostname=<KUBEFLOW_HOSTNAME> # e.g. https://mykubeflow.example.com/pipeline
```

Then, ensure that you use the pass the right settings before triggering a pipeline run. The following snippet will prove useful:

```python
import requests

from zenml.client import Client
from zenml.integrations.kubeflow.flavors.kubeflow_orchestrator_flavor import (
    KubeflowOrchestratorSettings,
)

NAMESPACE = "namespace_name"  # This is the user namespace for the profile you want to use
USERNAME = "admin"  # This is the username for the profile you want to use
PASSWORD = "abc123"  # This is the password for the profile you want to use


# Use client_username and client_password and ZenML will automatically fetch a session cookie
kubeflow_settings = KubeflowOrchestratorSettings(
    client_username=USERNAME,
    client_password=PASSWORD,
    user_namespace=NAMESPACE
)

# You can also pass the cookie in `client_args` directly
# kubeflow_settings = KubeflowOrchestratorSettings(
#     client_args={"cookies": session_cookie}, user_namespace=NAMESPACE
# )

@pipeline(
    settings={
        "orchestrator.kubeflow": kubeflow_settings
    }
):
    ...

if "__name__" == "__main__":
  # Run the pipeline
```

Note that the above is also currently not tested on all Kubeflow 
versions, so there might be further bugs with older Kubeflow versions. In this case, please reach out to us on [Slack](https://zenml.io/slack-invite).

### Using secrets in settings

The above example encoded the username and password in plain-text as settings. You can also set them as secrets.

```shell
zenml secrets-manager secret register kubeflow_secret \
    --username=admin \
    --password=abc123
```

And then you can use them in code:

```python
# Use client_username and client_password and ZenML will automatically fetch a session cookie
kubeflow_settings = KubeflowOrchestratorSettings(
    client_username="{{kubeflow_secret.username}}",  # secret reference
    client_password="{{kubeflow_secret.password}}",  # secret reference
    user_namespace="namespace_name"
)
```

See full documentation of using secrets within ZenML [here](../../advanced-guide/practical/secrets-management.md).

A concrete example of using the Kubeflow orchestrator can be found
[here](https://github.com/zenml-io/zenml/tree/main/examples/kubeflow_pipelines_orchestration).

For more information and a full list of configurable attributes of the Kubeflow orchestrator, check out the
[API Docs](https://apidocs.zenml.io/latest/integration_code_docs/integrations-kubeflow/#zenml.integrations.kubeflow.orchestrators.kubeflow_orchestrator.KubeflowOrchestrator).
