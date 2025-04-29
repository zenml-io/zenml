---
description: Orchestrating your pipelines to run on Kubernetes clusters.
---

# Kubernetes Orchestrator

Using the ZenML `kubernetes` integration, you can orchestrate and scale your ML pipelines on a [Kubernetes](https://kubernetes.io/) cluster without writing a single line of Kubernetes code.

This Kubernetes-native orchestrator is a minimalist, lightweight alternative to other distributed orchestrators like Airflow or Kubeflow.

Overall, the Kubernetes orchestrator is quite similar to the Kubeflow orchestrator in that it runs each pipeline step in a separate Kubernetes pod. However, the orchestration of the different pods is not done by Kubeflow but by a separate master pod that orchestrates the step execution via topological sort.

Compared to Kubeflow, this means that the Kubernetes-native orchestrator is faster and much simpler since you do not need to install and maintain Kubeflow on your cluster. The Kubernetes-native orchestrator is an ideal choice for teams in need of distributed orchestration that do not want to go with a fully-managed offering.

{% hint style="warning" %}
This component is only meant to be used within the context of a [remote ZenML deployment scenario](https://docs.zenml.io/getting-started/deploying-zenml/). Usage with a local ZenML deployment may lead to unexpected behavior!
{% endhint %}

## When to use it

You should use the Kubernetes orchestrator if:

* you're looking for a lightweight way of running your pipelines on Kubernetes.
* you're not willing to maintain [Kubeflow Pipelines](kubeflow.md) on your Kubernetes cluster.
* you're not interested in paying for managed solutions like [Vertex](vertex.md).

## How to deploy it

The Kubernetes orchestrator requires a Kubernetes cluster in order to run. There are many ways to deploy a Kubernetes cluster using different cloud providers or on your custom infrastructure, and we can't possibly cover all of them, but you can check out our [our production guide](https://docs.zenml.io/user-guides/production-guide).

If the above Kubernetes cluster is deployed remotely on the cloud, then another pre-requisite to use this orchestrator would be to deploy and connect to a [remote ZenML server](https://docs.zenml.io/getting-started/deploying-zenml/).

## How to use it

To use the Kubernetes orchestrator, we need:

*   The ZenML `kubernetes` integration installed. If you haven't done so, run

    ```shell
    zenml integration install kubernetes
    ```
* [Docker](https://www.docker.com) installed and running.
* A [remote artifact store](../artifact-stores/README.md) as part of your stack.
* A [remote container registry](../container-registries/README.md) as part of your stack.
* A Kubernetes cluster [deployed](kubernetes.md#how-to-deploy-it)
* [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl) installed and the name of the Kubernetes configuration context which points to the target cluster (i.e. run`kubectl config get-contexts` to see a list of available contexts) . This is optional (see below).

{% hint style="info" %}
It is recommended that you set up [a Service Connector](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/service-connectors-guide) and use it to connect ZenML Stack Components to the remote Kubernetes cluster, especially If you are using a Kubernetes cluster managed by a cloud provider like AWS, GCP or Azure, This guarantees that your Stack is fully portable on other environments and your pipelines are fully reproducible.
{% endhint %}

We can then register the orchestrator and use it in our active stack. This can be done in two ways:

1.  If you have [a Service Connector](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/service-connectors-guide) configured to access the remote Kubernetes cluster, you no longer need to set the `kubernetes_context` attribute to a local `kubectl` context. In fact, you don't need the local Kubernetes CLI at all. You can [connect the stack component to the Service Connector](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/service-connectors-guide#connect-stack-components-to-resources) instead:

    ```
    $ zenml orchestrator register <ORCHESTRATOR_NAME> --flavor kubernetes
    Running with active stack: 'default' (repository)
    Successfully registered orchestrator `<ORCHESTRATOR_NAME>`.

    $ zenml service-connector list-resources --resource-type kubernetes-cluster -e
    The following 'kubernetes-cluster' resources can be accessed by service connectors:
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
2.  if you don't have a Service Connector on hand and you don't want to [register one](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/service-connectors-guide#register-service-connectors) , the local Kubernetes `kubectl` client needs to be configured with a configuration context pointing to the remote cluster. The `kubernetes_context` stack component must also be configured with the value of that context:

    ```shell
    zenml orchestrator register <ORCHESTRATOR_NAME> \
        --flavor=kubernetes \
        --kubernetes_context=<KUBERNETES_CONTEXT>

    # Register and activate a stack with the new orchestrator
    zenml stack register <STACK_NAME> -o <ORCHESTRATOR_NAME> ... --set
    ```

{% hint style="info" %}
ZenML will build a Docker image called `<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>` which includes your code and use it to run your pipeline steps in Kubernetes. Check out [this page](https://docs.zenml.io/how-to/customize-docker-builds/) if you want to learn more about how ZenML builds these images and how you can customize them.
{% endhint %}

You can now run any ZenML pipeline using the Kubernetes orchestrator:

```shell
python file_that_runs_a_zenml_pipeline.py
```

If all went well, you should now see the logs of all Kubernetes pods in your terminal, and when running `kubectl get pods -n zenml`, you should also see that a pod was created in your cluster for each pipeline step.

### Interacting with pods via kubectl

For debugging, it can sometimes be handy to interact with the Kubernetes pods directly via kubectl. To make this easier, we have added the following labels to all pods:

* `run`: the name of the ZenML run.
* `pipeline`: the name of the ZenML pipeline associated with this run.

E.g., you can use these labels to manually delete all pods related to a specific pipeline:

```shell
kubectl delete pod -n zenml -l pipeline=kubernetes_example_pipeline
```

### Additional configuration

The Kubernetes orchestrator will by default use a Kubernetes namespace called `zenml` to run pipelines. In that namespace, it will automatically create a Kubernetes service account called `zenml-service-account` and grant it `edit` RBAC role in that namespace. To customize these settings, you can configure the following additional attributes in the Kubernetes orchestrator:

* `kubernetes_namespace`: The Kubernetes namespace to use for running the pipelines. The namespace must already exist in the Kubernetes cluster.
* `service_account_name`: The name of a Kubernetes service account to use for running the pipelines. If configured, it must point to an existing service account in the default or configured `namespace` that has associated RBAC roles granting permissions to create and manage pods in that namespace. This can also be configured as an individual pipeline setting in addition to the global orchestrator setting.
* `pass_zenml_token_as_secret`: By default, the Kubernetes orchestrator will pass a short-lived API token to authenticate to the ZenML server as an environment variable as part of the Pod manifest. If you want this token to be stored in a Kubernetes secret instead, set `pass_zenml_token_as_secret=True` when registering your orchestrator. If you do so, make sure the service connector that you configure for your has permissions to create Kubernetes secrets. Additionally, the service account used for the Pods running your pipeline must have permissions to delete secrets, otherwise the cleanup will fail and you'll be left with orphaned secrets.
* `pod_name_prefix`: Prefix for the pod names. A random suffix and the step name will be appended to create unique pod names.
* `pod_startup_timeout`: The maximum time to wait for a pending step pod to start (in seconds). The orchestrator will delete the pending pod after this time has elapsed and raise an error. If configured, the `pod_failure_retry_delay` and `pod_failure_backoff` settings will also be used to calculate the delay between retries.
* `pod_failure_retry_delay`: The delay (in seconds) between retries to create a step pod that fails to start.
* `pod_failure_max_retries`: The maximum number of retries to create a step pod that fails to start.
* `pod_failure_backoff`: The backoff factor to use for retrying to create a step pod that fails to start.
* `max_parallelism`: By default the Kubernetes orchestrator immediately spins up a pod for every step that can run already because all its upstream steps have finished. For
pipelines with many parallel steps, it can be desirable to limit the amount of parallel steps in order to reduce the load on the Kubernetes cluster. This option can be used
to specify the maximum amount of steps pods that can be running at any time.

For additional configuration of the Kubernetes orchestrator, you can pass `KubernetesOrchestratorSettings` which allows you to configure (among others) the following attributes:

* `pod_settings`: Node selectors, labels, affinity, and tolerations, secrets, environment variables, image pull secrets, the scheduler name and additional arguments to apply to the Kubernetes Pods running the steps of your pipeline. These can be either specified using the Kubernetes model objects or as dictionaries.
* `orchestrator_pod_settings`: Node selectors, labels, affinity, tolerations, secrets, environment variables and image pull secrets to apply to the Kubernetes Pod that is responsible for orchestrating the pipeline and starting the other Pods. These can be either specified using the Kubernetes model objects or as dictionaries.

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
        },
        # Pass values for any additional PodSpec attribute here, e.g.
        # a deadline after which the pod should be killed
        "additional_pod_spec_args": {
            "active_deadline_seconds": 30
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

### Define settings on the step level

You can also define settings on the step level, which will override the settings defined at the pipeline level. This is helpful when you want to run a specific step with a different configuration like affinity for more powerful hardware or a different Kubernetes service account. Learn more about the hierarchy of settings [here](https://docs.zenml.io/concepts/steps_and_pipelines/configuration).

```python
k8s_settings = KubernetesOrchestratorSettings(
    pod_settings={
        "node_selectors": {
            "cloud.google.com/gke-nodepool": "gpu-pool",
        },
        "tolerations": [
            V1Toleration(
                key="gpu",
                operator="Equal",
                value="present",
                effect="NoSchedule"
            ),
        ]
    }
)

@step(settings={"orchestrator": k8s_settings})
def train_model(data: dict) -> None:
    ...


@pipeline() 
def simple_ml_pipeline(parameter: int):
    ...
```

This code will now run the `train_model` step on a GPU-enabled node in the `gpu-pool` node pool while the rest of the pipeline can run on ordinary nodes.

Check out the [SDK docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-kubernetes.html#zenml.integrations.kubernetes) for a full list of available attributes and [this docs page](https://docs.zenml.io/concepts/steps_and_pipelines/configuration) for more information on how to specify settings.

For more information and a full list of configurable attributes of the Kubernetes orchestrator, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-kubernetes.html#zenml.integrations.kubernetes) .

### Enabling CUDA for GPU-backed hardware

Note that if you wish to use this orchestrator to run steps on a GPU, you will need to follow [the instructions on this page](https://docs.zenml.io/user-guides/tutorial/distributed-training/) to ensure that it works. It requires adding some extra settings customization and is essential to enable CUDA for the GPU to give its full acceleration.

### Running scheduled pipelines with Kubernetes

The Kubernetes orchestrator supports scheduling pipelines through Kubernetes CronJobs. This feature allows you to run your pipelines on a recurring schedule without manual intervention.

#### How scheduling works

When you add a schedule to a pipeline running on the Kubernetes orchestrator, ZenML:

1. Creates a Kubernetes CronJob resource instead of a regular Pod
2. Configures the CronJob to use the same container image, command, and settings as your pipeline
3. Sets the CronJob's schedule field to match your provided cron expression

The Kubernetes scheduler then takes over and handles executing your pipeline on schedule.

#### Setting up a scheduled pipeline

You can add a schedule to your pipeline using the `Schedule` class:

```python
from zenml.config.schedule import Schedule
from zenml import pipeline

@pipeline()
def my_kubernetes_pipeline():
    # Your pipeline steps here
    ...

# Create a schedule using a cron expression
schedule = Schedule(cron_expression="5 2 * * *")  # Runs at 2:05 AM daily

# Attach the schedule to your pipeline
scheduled_pipeline = my_kubernetes_pipeline.with_options(schedule=schedule)

# Run the pipeline once to register the schedule
scheduled_pipeline()
```

Cron expressions follow the standard format (`minute hour day-of-month month day-of-week`):

* `"0 * * * *"` - Run hourly at the start of the hour
* `"0 0 * * *"` - Run daily at midnight
* `"0 0 * * 0"` - Run weekly on Sundays at midnight
* `"0 0 1 * *"` - Run monthly on the 1st at midnight

#### Verifying your scheduled pipeline

To check that your pipeline has been scheduled correctly:

1. Using the ZenML CLI:
```shell
zenml pipeline schedule list
```

2. Using kubectl to check the created CronJob:
```shell
kubectl get cronjobs -n zenml
kubectl describe cronjob <cronjob-name> -n zenml
```

The CronJob name will be based on your pipeline name with a random suffix for uniqueness.

#### Managing scheduled pipelines

To view your scheduled jobs and their status:

```shell
# List all CronJobs
kubectl get cronjobs -n zenml

# Check Jobs created by the CronJob
kubectl get jobs -n zenml

# View logs of a running job
kubectl logs job/<job-name> -n zenml
```

To update a scheduled pipeline, you need to:

1. Delete the existing CronJob from Kubernetes
2. Create a new pipeline with the updated schedule

```shell
# Delete the existing CronJob
kubectl delete cronjob <cronjob-name> -n zenml
```

```python
# Create a new schedule
new_schedule = Schedule(cron_expression="0 4 * * *")  # Now runs at 4 AM
updated_pipeline = my_kubernetes_pipeline.with_options(schedule=new_schedule)
updated_pipeline()
```

#### Deleting a scheduled pipeline

When you no longer need a scheduled pipeline, you must delete both the ZenML schedule and the Kubernetes CronJob:

1. Delete the schedule from ZenML:
```python
from zenml.client import Client

client = Client()
client.delete_schedule("<schedule-name>")
```

2. Delete the CronJob from Kubernetes:
```shell
kubectl delete cronjob <cronjob-name> -n zenml
```

{% hint style="warning" %}
Deleting just the ZenML schedule will not stop the recurring executions. You must delete the Kubernetes CronJob as well.
{% endhint %}

#### Troubleshooting

If your scheduled pipeline isn't running as expected:

1. Verify the CronJob exists and has the correct schedule:
```shell
kubectl get cronjob <cronjob-name> -n zenml
```

2. Check the CronJob's recent events and status:
```shell
kubectl describe cronjob <cronjob-name> -n zenml
```

3. Look at logs from recent job executions:
```shell
kubectl logs job/<job-name> -n zenml
```

Common issues include incorrect cron expressions, insufficient permissions for the service account, or resource constraints.

For a tutorial on how to work with schedules in ZenML, check out our ['Managing
Scheduled
Pipelines'](https://docs.zenml.io/user-guides/tutorial/managing-scheduled-pipelines)
docs page.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
