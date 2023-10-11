---
description: How to orchestrate pipelines with Tekton
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The Tekton orchestrator is an [orchestrator](./orchestrators.md) flavor provided with
the ZenML `tekton` integration that uses
[Tekton Pipelines](https://tekton.dev/) to run your pipelines.

## When to use it

You should use the Tekton orchestrator if:

* you're looking for a proven production-grade orchestrator.
* you're looking for a UI in which you can track your pipeline
runs.
* you're already using Kubernetes or are not afraid of 
setting up and maintaining a Kubernetes cluster.
* you're willing to deploy and maintain Tekton Pipelines
on your cluster.

## How to deploy it

You'll first need to
set up a Kubernetes cluster and deploy Tekton Pipelines:

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
* [Install](https://tekton.dev/docs/pipelines/install/)
  Tekton Pipelines onto your cluster.
  {% endtab %}

{% tab title="GCP" %}

* Have an existing
  GCP [GKE cluster](https://cloud.google.com/kubernetes-engine/docs/quickstart)
  set up.
* Make sure you have the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install-sdk) set up first.
* Download and [install](https://kubernetes.io/docs/tasks/tools/) `kubectl`
  and [configure](https://cloud.google.com/kubernetes-engine/docs/how-to/cluster-access-for-kubectl)
  it to talk to your GKE cluster using the following command:

  ```powershell
  gcloud container clusters get-credentials CLUSTER_NAME
  ```
* [Install](https://tekton.dev/docs/pipelines/install/)
  Tekton Pipelines onto your cluster.
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
* [Install](https://tekton.dev/docs/pipelines/install/)
  Tekton Pipelines onto your cluster.
{% endtab %}
{% endtabs %}

{% hint style="info" %}
If one or more of the deployments are not in the `Running` state, try increasing
the number of nodes in your cluster.
{% endhint %}

{% hint style="warning" %}
ZenML has only been tested with Tekton Pipelines >=0.38.3 and may not work with previous 
versions.
{% endhint %}

## How to use it

To use the Tekton orchestrator, we need:
* The ZenML `tekton` integration installed. If you haven't done so, run 
    ```shell
    zenml integration install tekton -y
    ```
* [Docker](https://www.docker.com) installed and running.
* [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl) installed.
* Tekton pipelines deployed on a remote cluster. See the [deployment section](#how-to-deploy-it) 
for more information.
* The name of your Kubernetes context which points to your remote cluster. 
Run `kubectl config get-contexts` to see a list of available contexts.
* A [remote artifact store](../artifact-stores/artifact-stores.md) as part of your stack.
* A [remote metadata store](../metadata-stores/metadata-stores.md) as part of your stack. We suggest
using a [MySQL metatadata store](../metadata-stores/mysql.md).
* A [remote container registry](../container-registries/container-registries.md) as part of your stack.

We can then register the orchestrator and use it in our active stack:
```shell
zenml orchestrator register <NAME> \
    --flavor=tekton \
    --kubernetes_context=<KUBERNETES_CONTEXT>

# Add the orchestrator to the active stack
zenml stack update -o <NAME>
```

{% hint style="info" %}
ZenML will build a Docker image called `<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>`
which includes your code and use it to run your pipeline steps in Tekton. Check out
[this page](../../developer-guide/advanced-usage/docker.md)
if you want to learn more about how ZenML builds these images and
how you can customize them.
{% endhint %}

Once the orchestrator is part of the active stack, we need to run
`zenml stack up` before running any pipelines. This command forwards a port so 
you can view the Tekton UI in your browser.

You can now run any ZenML pipeline using the Tekton orchestrator:
```shell
python file_that_runs_a_zenml_pipeline.py
```

A concrete example of using the Tekton orchestrator can be found 
[here](https://github.com/zenml-io/zenml/tree/main/examples/tekton_pipelines_orchestration).

For more information and a full list of configurable attributes of the Tekton orchestrator, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.tekton.orchestrators.tekton_orchestrator.TektonOrchestrator).