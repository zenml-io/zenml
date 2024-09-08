---
description: Orchestrating your pipelines to run on Kubernetes clusters.
---

# Kubernetes Orchestrator

Using the ZenML `kubernetes` integration, you can orchestrate and scale your ML pipelines on a [Kubernetes](https://kubernetes.io/) cluster without writing a single line of Kubernetes code.

This Kubernetes-native orchestrator is a minimalist, lightweight alternative to other distributed orchestrators like Airflow or Kubeflow.

Overall, the Kubernetes orchestrator is quite similar to the Kubeflow orchestrator in that it runs each pipeline step in a separate Kubernetes pod. However, the orchestration of the different pods is not done by Kubeflow but by a separate master pod that orchestrates the step execution via topological sort.

Compared to Kubeflow, this means that the Kubernetes-native orchestrator is faster and much simpler to start with since you do not need to install and maintain Kubeflow on your cluster. The Kubernetes-native orchestrator is an ideal choice for teams new to distributed orchestration that do not want to go with a fully-managed offering.

However, since Kubeflow is much more mature, you should, in most cases, aim to move your pipelines to Kubeflow in the long run. A smooth way to production-grade orchestration could be to set up a Kubernetes cluster first and get started with the Kubernetes-native orchestrator. If needed, you can then install and set up Kubeflow later and simply switch out the orchestrator of your stack as soon as your full setup is ready.

{% hint style="warning" %}
This component is only meant to be used within the context of a [remote ZenML deployment scenario](../../getting-started/deploying-zenml/README.md). Usage with a local ZenML deployment may lead to unexpected behavior!
{% endhint %}

### When to use it

You should use the Kubernetes orchestrator if:

* you're looking for a lightweight way of running your pipelines on Kubernetes.
* you're not willing to maintain [Kubeflow Pipelines](kubeflow.md) on your Kubernetes cluster.
* you're not interested in paying for managed solutions like [Vertex](vertex.md).

### How to deploy it

The Kubernetes orchestrator requires a Kubernetes cluster in order to run. There are many ways to deploy a Kubernetes cluster using different cloud providers or on your custom infrastructure, and we can't possibly cover all of them, but you can check out our cloud guide

If the above Kubernetes cluster is deployed remotely on the cloud, then another pre-requisite to use this orchestrator would be to deploy and connect to a [remote ZenML server](../../getting-started/deploying-zenml/README.md).

#### Infrastructure Deployment

A Kubernetes orchestrator can be deployed directly from the ZenML CLI:

```shell
zenml orchestrator deploy k8s_orchestrator --flavor=kubernetes --provider=<YOUR_PROVIDER> ...
```

You can pass other configurations specific to the stack components as key-value arguments. If you don't provide a name, a random one is generated for you. For more information about how to work use the CLI for this, please refer to the dedicated documentation section.

### How to use it

To use the Kubernetes orchestrator, we need:

*   The ZenML `kubernetes` integration installed. If you haven't done so, run

    ```shell
    zenml integration install kubernetes
    ```
* [Docker](https://www.docker.com) installed and running.
* [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl) installed.
* A [remote artifact store](../artifact-stores/artifact-stores.md) as part of your stack.
* A [remote container registry](../container-registries/container-registries.md) as part of your stack.
* A Kubernetes cluster [deployed](kubernetes.md#how-to-deploy-it)
* [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl) installed and the name of the Kubernetes configuration context which points to the target cluster (i.e. run`kubectl config get-contexts` to see a list of available contexts) . This is optional (see below).

{% hint style="info" %}
It is recommended that you set up [a Service Connector](../../how-to/auth-management/service-connectors-guide.md) and use it to connect ZenML Stack Components to the remote Kubernetes cluster, especially If you are using a Kubernetes cluster managed by a cloud provider like AWS, GCP or Azure, This guarantees that your Stack is fully portable on other environments and your pipelines are fully reproducible.
{% endhint %}

We can then register the orchestrator and use it in our active stack. This can be done in two ways:

1.  If you have [a Service Connector](../../how-to/auth-management/service-connectors-guide.md) configured to access the remote Kubernetes cluster, you no longer need to set the `kubernetes_context` attribute to a local `kubectl` context. In fact, you don't need the local Kubernetes CLI at all. You can [connect the stack component to the Service Connector](../../how-to/auth-management/service-connectors-guide.md#connect-stack-components-to-resources) instead:

    ```
    $ zenml orchestrator register <ORCHESTRATOR_NAME> --flavor kubernetes
    Running with active workspace: 'default' (repository)
    Running with active stack: 'default' (repository)
    Successfully registered orchestrator `<ORCHESTRATOR_NAME>`.

    $ zenml service-connector list-resources --resource-type kubernetes-cluster -e
    The following 'kubernetes-cluster' resources can be accessed by service connectors configured in your workspace:
    ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━┓
    ┃             CONNECTOR ID             │ CONNECTOR NAME        │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES      ┃
    ┠──────────────────────────────────────┼───────────────────────┼────────────────┼───────────────────────┼─────────────────────┨
    ┃ e33c9fac-5daa-48b2-87bb-0187d3782cde │ aws-iam-multi-eu      │ 🔶 aws         │ 🌀 kubernetes-cluster │ kubeflowmultitenant ┃
    ┃                                      │                       │                │                       │ zenbox              ┃
    ┠──────────────────────────────────────┼───────────────────────┼────────────────┼───────────────────────┼─────────────────────┨
    ┃ ed528d5a-d6cb-4fc4-bc52-c3d2d01643e5 │ aws-iam-multi-us      │ 🔶 aws         │ 🌀 kubernetes-cluster │ zenhacks-cluster    ┃
    ┠──────────────────────────────────────┼───────────────────────┼────────────────┼───────────────────────┼─────────────────────┨
    ┃ 1c54b32a-4889-4417-abbd-42d3ace3d03a │ gcp-sa-multi          │ 🔵 gcp         │ 🌀 kubernetes-cluster │ zenml-test-cluster  ┃
    ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━┛

    $ zenml orchestrator connect <ORCHESTRATOR_NAME> --connector aws-iam-multi-us
    Running with active workspace: 'default' (repository)
    Running with active stack: 'default' (repository)
    Successfully connected orchestrator `<ORCHESTRATOR_NAME>` to the following resources:
    ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━┓
    ┃             CONNECTOR ID             │ CONNECTOR NAME   │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES   ┃
    ┠──────────────────────────────────────┼──────────────────┼────────────────┼───────────────────────┼──────────────────┨
    ┃ ed528d5a-d6cb-4fc4-bc52-c3d2d01643e5 │ aws-iam-multi-us │ 🔶 aws         │ 🌀 kubernetes-cluster │ zenhacks-cluster ┃
    ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━┛

    # Register and activate a stack with the new orchestrator
    $ zenml stack register <STACK_NAME> -o <ORCHESTRATOR_NAME> ... --set
    ```
2.  if you don't have a Service Connector on hand and you don't want to [register one](../../how-to/auth-management/service-connectors-guide.md#register-service-connectors) , the local Kubernetes `kubectl` client needs to be configured with a configuration context pointing to the remote cluster. The `kubernetes_context` stack component must also be configured with the value of that context:

    ```shell
    zenml orchestrator register <ORCHESTRATOR_NAME> \
        --flavor=kubernetes \
        --kubernetes_context=<KUBERNETES_CONTEXT>

    # Register and activate a stack with the new orchestrator
    zenml stack register <STACK_NAME> -o <ORCHESTRATOR_NAME> ... --set
    ```

{% hint style="info" %}
ZenML will build a Docker image called `<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>` which includes your code and use it to run your pipeline steps in Kubernetes. Check out [this page](../../how-to/customize-docker-builds/README.md) if you want to learn more about how ZenML builds these images and how you can customize them.
{% endhint %}

You can now run any ZenML pipeline using the Kubernetes orchestrator:

```shell
python file_that_runs_a_zenml_pipeline.py
```

If all went well, you should now see the logs of all Kubernetes pods in your terminal, and when running `kubectl get pods -n zenml`, you should also see that a pod was created in your cluster for each pipeline step.

#### Interacting with pods via kubectl

For debugging, it can sometimes be handy to interact with the Kubernetes pods directly via kubectl. To make this easier, we have added the following labels to all pods:

* `run`: the name of the ZenML run.
* `pipeline`: the name of the ZenML pipeline associated with this run.

E.g., you can use these labels to manually delete all pods related to a specific pipeline:

```shell
kubectl delete pod -n zenml -l pipeline=kubernetes_example_pipeline
```

#### Additional configuration

The Kubernetes orchestrator will by default use a Kubernetes namespace called `zenml` to run pipelines. In that namespace, it will automatically create a Kubernetes service account called `zenml-service-account` and grant it `edit` RBAC role in that namespace. To customize these settings, you can configure the following additional attributes in the Kubernetes orchestrator:

* `kubernetes_namespace`: The Kubernetes namespace to use for running the pipelines. The namespace must already exist in the Kubernetes cluster.
* `service_account_name`: The name of a Kubernetes service account to use for running the pipelines. If configured, it must point to an existing service account in the default or configured `namespace` that has associated RBAC roles granting permissions to create and manage pods in that namespace. This can also be configured as an individual pipeline setting in addition to the global orchestrator setting.

For additional configuration of the Kubernetes orchestrator, you can pass `KubernetesOrchestratorSettings` which allows you to configure (among others) the following attributes:

* `pod_settings`: Node selectors, labels, affinity, and tolerations, and image pull secrets to apply to the Kubernetes Pods running the steps of your pipeline. These can be either specified using the Kubernetes model objects or as dictionaries.

* `orchestrator_pod_settings`:  Node selectors, labels, affinity, and tolerations, and image pull secrets to apply to the Kubernetes Pod that is responsible for orchestrating the pipeline and starting the other Pods. These can be either specified using the Kubernetes model objects or as dictionaries.

```python
from zenml.integrations.kubernetes.flavors.kubernetes_orchestrator_flavor import KubernetesOrchestratorSettings
from kubernetes.client.models import V1Toleration

kubernetes_settings = KubernetesOrchestratorSettings(
    pod_settings={
        "node_selectors": {
            "cloud.google.com/gke-nodepool": "ml-pool",
            "kubernetes.io/arch": "amd64"
        },
        "affinity": {
            "nodeAffinity": {
                "requiredDuringSchedulingIgnoredDuringExecution": {
                    "nodeSelectorTerms": [
                        {
                            "matchExpressions": [
                                {
                                    "key": "gpu-type",
                                    "operator": "In",
                                    "values": ["nvidia-tesla-v100", "nvidia-tesla-p100"]
                                }
                            ]
                        }
                    ]
                }
            }
        },
        "tolerations": [
            V1Toleration(
                key="gpu",
                operator="Equal",
                value="present",
                effect="NoSchedule"
            ),
            V1Toleration(
                key="high-priority",
                operator="Exists",
                effect="PreferNoSchedule"
            )
        ],
        "resources": {
            "requests": {
                "cpu": "2",
                "memory": "4Gi",
                "nvidia.com/gpu": "1"
            },
            "limits": {
                "cpu": "4",
                "memory": "8Gi",
                "nvidia.com/gpu": "1"
            }
        },
        "annotations": {
            "prometheus.io/scrape": "true",
            "prometheus.io/port": "8080"
        },
        "volumes": [
            {
                "name": "data-volume",
                "persistentVolumeClaim": {
                    "claimName": "ml-data-pvc"
                }
            },
            {
                "name": "config-volume",
                "configMap": {
                    "name": "ml-config"
                }
            }
        ],
        "volume_mounts": [
            {
                "name": "data-volume",
                "mountPath": "/mnt/data"
            },
            {
                "name": "config-volume",
                "mountPath": "/etc/ml-config",
                "readOnly": True
            }
        ],
        "host_ipc": True,
        "image_pull_secrets": ["regcred", "gcr-secret"],
        "labels": {
            "app": "ml-pipeline",
            "environment": "production",
            "team": "data-science"
        }
    },
    orchestrator_pod_settings={
        "node_selectors": {
            "cloud.google.com/gke-nodepool": "orchestrator-pool"
        },
        "resources": {
            "requests": {
                "cpu": "1",
                "memory": "2Gi"
            },
            "limits": {
                "cpu": "2",
                "memory": "4Gi"
            }
        },
        "labels": {
            "app": "zenml-orchestrator",
            "component": "pipeline-runner"
        }
    },
    kubernetes_namespace="ml-pipelines",
    service_account_name="zenml-pipeline-runner"
)

@pipeline(
    settings={
        "orchestrator": kubernetes_settings
    }
)
def my_kubernetes_pipeline():
    # Your pipeline steps here
    ...
```

Check out the [SDK docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-kubernetes/#zenml.integrations.kubernetes.flavors.kubernetes\_orchestrator\_flavor.KubernetesOrchestratorSettings) for a full list of available attributes and [this docs page](../../how-to/use-configuration-files/runtime-configuration.md) for more information on how to specify settings.

For more information and a full list of configurable attributes of the Kubernetes orchestrator, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-kubernetes/#zenml.integrations.kubernetes.orchestrators.kubernetes\_orchestrator.KubernetesOrchestrator) .

#### Enabling CUDA for GPU-backed hardware

Note that if you wish to use this orchestrator to run steps on a GPU, you will need to follow [the instructions on this page](../../how-to/training-with-gpus/training-with-gpus.md) to ensure that it works. It requires adding some extra settings customization and is essential to enable CUDA for the GPU to give its full acceleration.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
