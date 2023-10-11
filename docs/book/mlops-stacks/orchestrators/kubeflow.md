---
description: How to orchestrate pipelines with Kubeflow
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The Kubeflow orchestrator is an [orchestrator](./orchestrators.md) flavor provided with
the ZenML `kubeflow` integration that uses
[Kubeflow Pipelines](https://www.kubeflow.org/docs/components/pipelines/introduction/)
to run your pipelines.

## When to use it

You should use the Kubeflow orchestrator if:
* you're looking for a proven production-grade orchestrator.
* you're looking for a UI in which you can track your pipeline
runs.
* you're already using Kubernetes or are not afraid of 
setting up and maintaining a Kubernetes cluster.
* you're willing to deploy and maintain Kubeflow Pipelines
on your cluster.

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
* Make sure you have the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install-sdk) set up first.
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
to [`containerd`](https://docs.microsoft.com/en-us/azure/aks/cluster-configuration#container-runtime-configuration)
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

When using the Kubeflow orchestrator locally, you'll additionally need
* [K3D](https://k3d.io/v5.2.1/#installation) installed to spin up a local Kubernetes
cluster.
* A [local container registry](../container-registries/default.md) as part of your stack.

{% hint style="warning" %}
The local Kubeflow Pipelines deployment requires more than 2 GB of RAM,
so if you're using Docker Desktop make sure to update the resource
limits in the preferences.
{% endhint %}

We can then register the orchestrator and use it in our active stack:
```shell
zenml orchestrator register <NAME> \
    --flavor=kubeflow

# Add the orchestrator to the active stack
zenml stack update -o <NAME>
```

{% endtab %}

{% tab title="Remote" %}

When using the Kubeflow orchestrator with a remote cluster, you'll additionally need
* Kubeflow pipelines deployed on a remote cluster. See the [deployment section](#how-to-deploy-it) 
for more information.
* The name of your Kubernetes context which points to your remote cluster. 
Run `kubectl config get-contexts` to see a list of available contexts.
* A [remote artifact store](../artifact-stores/artifact-stores.md) as part of your stack.
* A [remote metadata store](../metadata-stores/metadata-stores.md) as part of your stack. Kubeflow Pipelines
already comes with its own MySQL database that is deployed in your Kubernetes cluster. If you want
to use this database as your metadata store to get started quickly, check out the corresponding
[documentation page](../metadata-stores/kubeflow.md). For a more production-ready setup we suggest
using a [MySQL metatadata store](../metadata-stores/mysql.md) instead.
* A [remote container registry](../container-registries/container-registries.md) as part of your stack.

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
which includes your code and use it to run your pipeline steps in Kubeflow. Check out
[this page](../../developer-guide/advanced-usage/docker.md)
if you want to learn more about how ZenML builds these images and
how you can customize them.
{% endhint %}

Once the orchestrator is part of the active stack, we need to run
`zenml stack up` before running any pipelines. This command
* forwards a port so you can view the Kubeflow UI in your browser.
* (in the local case) uses K3D to provision a Kubernetes cluster
on your machine and deploys Kubeflow Pipelines on it.

You can now run any ZenML pipeline using the Kubeflow orchestrator:
```shell
python file_that_runs_a_zenml_pipeline.py
```

A concrete example of using the Kubeflow orchestrator can be found 
[here](https://github.com/zenml-io/zenml/tree/main/examples/kubeflow_pipelines_orchestration).

For more information and a full list of configurable attributes of the Kubeflow orchestrator, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.kubeflow.orchestrators.kubeflow_orchestrator.KubeflowOrchestrator).

## Important Note for Multi-Tenancy Deployments

Kubeflow has a notion of [multi-tenancy](https://www.kubeflow.org/docs/components/multi-tenancy/overview/) 
built into its deployment. Kubeflow’s multi-user isolation simplifies user 
operations because each user only views and edited\s the Kubeflow components 
and model artifacts defined in their configuration.

Currently, the default ZenML Kubeflow orchestrator yields the following error 
when running a pipeline:

```shell
HTTP response body: {"error":"Invalid input error: Invalid resource references for experiment. ListExperiment requires filtering by namespace.","code":3,"message":"Invalid input error: Invalid resource references for experiment. ListExperiment requires filtering by 
namespace.","details":[{"@type":"type.googleapis.com/api.Error","error_message":"Invalid resource references for experiment. ListExperiment requires filtering by namespace.","error_details":"Invalid input error: Invalid resource references for experiment. ListExperiment requires filtering by namespace."}]}
```

The current workaround is as follows. Please place the following code at the top of your runner script (commonly called `run.py`):

```python
import json
import os
import kfp
import os 
from kubernetes import client as k8s_client

NAMESPACE = "namespace_name"  # set this
USERNAME = "foo"  # set this
PASSWORD = "bar"  # set this
HOST = "https://qux.com" # set this
KFP_CONFIG = '~/.config/kfp/context.json'  # set this manually if  you'd like

def get_kfp_token(username: str, password: str) -> str:
    """Get token for kubeflow authentication."""
    session = requests.Session()
    response = session.get(HOST)
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"login": username, "password": password}
    session.post(response.url, headers=headers, data=data)
    session_cookie = session.cookies.get_dict()["authservice_session"]
    return session_cookie

token = get_kfp_token()
cookies = 'authservice_session=' + token

# 1: Set user namespace globally
kfp.Client(host=HOST, cookies=cookies).set_user_namespace(NAMESPACE)

# 2: Set cookie globally in the kfp config file
with open(KFP_CONFIG, 'r') as f:
    data = json.load(f)
    data['client_authentication_cookie'] = cookies

os.remove(KFP_CONFIG)
with open(KFP_CONFIG, 'w') as f:
    json.dump(data, f)

original = KubeflowOrchestrator._configure_container_op

def patch_container_op(container_op):
    original(container_op)
    container_op.container.add_env_variable(
        k8s_client.V1EnvVar(name="ZENML_RUN_NAME", value="{{workflow.annotations.pipelines.kubeflow.org/run_name}}")
    )

KubeflowOrchestrator._configure_container_op = staticmethod(patch_container_op)

def patch_get_run_name(self, pipeline_name):
    return os.getenv("ZENML_RUN_NAME")

KubeflowEntrypointConfiguration.get_run_name = patch_get_run_name

# Continue with your normal pipeline runner code..
```

Please note that in the above code, `HOST` should be registered on orchestration registration, 
with the `kubeflow_hostname` parameter:

```
export HOST=https://qux.com
zenml orchestrator register multi_tenant_kf --flavor=kubeflow \
   --kubeflow_hostname=$(HOST)/pipeline  # /pipeline is important!
   --other_params..
```

Further note that the above is also currently not tested on all Kubeflow versions, so there might be further bugs with older Kubeflow versions. In this case, please reach out to us on [Slack](https://zenml.io/slack-invite).

In future ZenML versions, multi-tenancy will be natively supported. See this 
[Slack thread](https://zenml.slack.com/archives/C01FWQ5D0TT/p1662545810395779) for more details  
on how the above workaround came to effect.

Please note that the above is all to initialize the `kfp.Client()` class in the standard orchestrator logic. 
This code can be seen [here](https://github.com/zenml-io/zenml/blob/main/src/zenml/integrations/kubeflow/orchestrators/kubeflow_orchestrator.py#L709).

You can simply override this logic and add your custom authentication scheme if needed. Read [here](custom.md) 
for more details on how to create a custom orchestrator.