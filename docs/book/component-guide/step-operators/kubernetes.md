---
description: Executing individual steps in Kubernetes Pods.
---

# Kubernetes

ZenML's Kubernetes step operator allows you to submit individual steps to be run on Kubernetes pods.

### When to use it

You should use the Kubernetes step operator if:

* one or more steps of your pipeline require computing resources (CPU, GPU, memory) that are not provided by your orchestrator.
* you have access to a Kubernetes cluster.

### How to deploy it

The Kubernetes step operator requires a Kubernetes cluster in order to run. There are many ways to deploy a Kubernetes cluster using different cloud providers or on your custom infrastructure, and we can't possibly cover all of them, but you can check out our cloud guide.

### How to use it

To use the Kubernetes step operator, we need:

*   The ZenML `kubernetes` integration installed. If you haven't done so, run

    ```shell
    zenml integration install kubernetes
    ```
* A Kubernetes cluster [deployed](kubernetes.md#how-to-deploy-it)
* Either [Docker](https://www.docker.com) installed and running or a remote [image builder](https://docs.zenml.io/stacks/image-builders/) in your stack.
* A [remote artifact store](https://docs.zenml.io/stacks/artifact-stores/) as part of your stack. This is needed so that both your orchestration environment and Kubernetes Pods can read and write step artifacts. Check out the documentation page of the artifact store you want to use for more information on how to set that up and configure authentication for it.

{% hint style="info" %}
It is recommended that you set up [a Service Connector](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/service-connectors-guide) and use it to connect the Kubernetes step operator to the Kubernetes cluster, especially if you are using a Kubernetes cluster managed by a cloud provider like AWS, GCP or Azure.
{% endhint %}

We can then register the step operator and use it in our stacks. This can be done in two ways:

1.  Using a Service Connector configured to access the remote Kubernetes cluster. Depending on your cloud provider, this should be either an [AWS](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/aws-service-connector), [Azure](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/azure-service-connector) or [GCP](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/gcp-service-connector) service connector. If you're using a Kubernetes cluster that is not provided by any of these, you can use the generic [Kubernetes](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/kubernetes-service-connector) service connector. You can then [connect the stack component to the Service Connector](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/service-connectors-guide#connect-stack-components-to-resources):

    ```
    $ zenml step-operator register <NAME> --flavor kubernetes
    Running with active stack: 'default' (repository)
    Successfully registered step operator `<NAME>`.

    $ zenml service-connector list-resources --resource-type kubernetes-cluster -e
    The following 'kubernetes-cluster' resources can be accessed by service connectors that you have configured:
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

    $ zenml step-operator connect <NAME> --connector aws-iam-multi-us
    Running with active stack: 'default' (repository)
    Successfully connected step_operator `<NAME>` to the following resources:
    ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━┓
    ┃             CONNECTOR ID             │ CONNECTOR NAME   │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES   ┃
    ┠──────────────────────────────────────┼──────────────────┼────────────────┼───────────────────────┼──────────────────┨
    ┃ ed528d5a-d6cb-4fc4-bc52-c3d2d01643e5 │ aws-iam-multi-us │ 🔶 aws         │ 🌀 kubernetes-cluster │ zenhacks-cluster ┃
    ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━┛
    ```
2.  Using the local Kubernetes `kubectl` client. This client needs to be configured with a configuration context pointing to the remote cluster. The `kubernetes_context` configuration attribute must also be configured with the value of that context:

    ```shell
    zenml step-operator register <NAME> \
        --flavor=kubernetes \
        --kubernetes_context=<KUBERNETES_CONTEXT>
    ```

We can then use the registered step operator in our active stack:

```shell
# Add the step operator to the active stack
zenml stack update -s <NAME>
```

Once you added the step operator to your active stack, you can use it to execute individual steps of your pipeline by specifying it in the `@step` decorator as follows:

```python
from zenml import step


@step(step_operator=True)
def trainer(...) -> ...:
    """Train a model."""
    # This step will be executed in Kubernetes.
```

{% hint style="info" %}
ZenML will build a Docker images which includes your code and use it to run your steps in Kubernetes. Check out [this page](https://docs.zenml.io/how-to/customize-docker-builds/) if you want to learn more about how ZenML builds these images and how you can customize them.
{% endhint %}

#### Interacting with pods via kubectl

For debugging, it can sometimes be handy to interact with the Kubernetes pods directly via kubectl. To make this easier, we have added the following labels to all pods:

* `run`: the name of the ZenML run.
* `pipeline`: the name of the ZenML pipeline associated with this run.

E.g., you can use these labels to manually delete all pods related to a specific pipeline:

```shell
kubectl delete pod -n zenml -l pipeline=kubernetes_example_pipeline
```

#### Additional configuration

Some configuration options for the Kubernetes step operator can only be set through the step operator config when you register it (and cannot be changed per-run or per-step through the settings):

- **`kubernetes_namespace`** (default: "zenml"): The Kubernetes namespace to use for running the step pods. The namespace must already exist in the Kubernetes cluster.
- **`incluster`** (default: False): If `True`, the step operator will run the step inside the same Kubernetes cluster as the orchestrator, ignoring the `kubernetes_context`.
- **`kubernetes_context`**: The name of the Kubernetes context to use for running steps (ignored if using a service connector or `incluster`).

The following configuration options can be set either through the step operator config or overridden using `KubernetesStepOperatorSettings`:

- **`pod_settings`**: Node selectors, labels, affinity, tolerations, secrets, environment variables and image pull secrets to apply to the Kubernetes Pods. These can be either specified using the Kubernetes model objects or as dictionaries.
- **`service_account_name`**: Name of the service account to use for the pod.
- **`privileged`** (default: False): If the container should be run in privileged mode.
- **`pod_startup_timeout`** (default: 600): The maximum time (in seconds) to wait for a pending step pod to start.
- **`pod_failure_max_retries`** (default: 3): The maximum number of times to retry a step pod if it fails to start.
- **`pod_failure_retry_delay`** (default: 10): The delay (in seconds) between pod failure retries and pod startup retries.
- **`pod_failure_backoff`** (default: 1.0): The backoff factor for pod failure retries and pod startup retries.

```python
from zenml.integrations.kubernetes.flavors import KubernetesStepOperatorSettings
from kubernetes.client.models import V1Toleration

kubernetes_settings = KubernetesStepOperatorSettings(
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
        "env": [
            {
                "name": "MY_ENVIRONMENT_VARIABLE",
                "value": "1",
            }
        ],
        "env_from": [
            {
                "secretRef": {
                    "name": "secret-name",
                }
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
    service_account_name="zenml-pipeline-runner"
)

@step(
    settings={
        "step_operator": kubernetes_settings
    }
)
def my_kubernetes_step():
    ...
```

Check out the [SDK docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-kubernetes.html#zenml.integrations.kubernetes) for a full list of available attributes and [this docs page](https://docs.zenml.io/concepts/steps_and_pipelines/configuration) for more information on how to specify settings.

For more information and a full list of configurable attributes of the Kubernetes steop operator, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-kubernetes.html#zenml.integrations.kubernetes) .

#### Enabling CUDA for GPU-backed hardware

Note that if you wish to use this step operator to run steps on a GPU, you will need to follow [the instructions on this page](https://docs.zenml.io/user-guides/tutorial/distributed-training/) to ensure that it works. It requires adding some extra settings customization and is essential to enable CUDA for the GPU to give its full acceleration.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
