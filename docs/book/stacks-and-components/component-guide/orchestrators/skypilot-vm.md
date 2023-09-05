---
description: Orchestrating your pipelines to run on VMs using SkyPilot.
---

# AWS Sagemaker Orchestrator

The SkyPilot VM Orchestrator is a new integration provided by ZenML that allows you to
provision and manage virtual machines (VMs) on any cloud provider using the [SkyPilot framework](https://skypilot.readthedocs.io/en/latest/index.html).
This integration is designed to simplify the process of running machine learning workloads
on the cloud, offering cost savings, high GPU availability, and managed execution.

{% hint style="warning" %}
This component is only meant to be used within the context of
a [remote ZenML deployment scenario](/docs/book/deploying-zenml/zenml-self-hosted/zenml-self-hosted.md).
Usage with a local ZenML deployment may lead to unexpected behavior!
{% endhint %}

## When to use it

You should use the SkyPilot VM Orchestrator if:

* you want to maximize cost savings by leveraging spot VMs and auto-picking the cheapest VM/zone/region/cloud.
* you want to ensure high GPU availability by provisioning VMs in all zones/regions/clouds you have access to.
* you don't need a UI to list all your pipeline runs.
* you're not willing to maintain Kubernetes based solution or in paying for managed solutions like [Sagemaker](sagemaker.md).


## How it works

The SkyPilot VM Orchestrator integrates with the ZenML pipeline framework, allowing you to easily
incorporate VM provisioning and management into your ML workflows. It abstracts away the complexities
of managing cloud infrastructure, making it simple to launch jobs and clusters on any cloud provider.

The orchestrator leverages the SkyPilot framework to handle the provisioning and scaling of VMs.
It automatically manages the process of launching VMs on different cloud providers, ensuring maximum
cost savings and GPU availability.

One of the key features of the SkyPilot VM Orchestrator is its ability to maximize GPU availability.
It achieves this by provisioning VMs in all available zones, regions, and clouds, with automatic failover.
This ensures that your jobs can make the most efficient use of GPU resources.

Additionally, the SkyPilot VM Orchestrator offers cost savings through various mechanisms.
It leverages managed spot VMs, which can provide significant cost savings compared to on-demand VMs.
The integration also includes an optimizer that automatically selects the cheapest VM/zone/region/cloud
for your workloads, further reducing costs. Finally, the orchestrator includes an autostop feature that
cleans up idle clusters, preventing unnecessary cloud costs.

The SkyPilot VM Orchestrator seamlessly supports your existing GPU, TPU, and CPU workloads, requiring
no code changes. It provides a unified interface for provisioning and managing VMs across different cloud
providers, making it easy to run your machine learning workloads in a cost-effective and efficient manner.

{% hint style="warning" %}
The SkyPilot VM Orchestrator does not currently support the ability to [schedule pipelines runs](https://docs.zenml.io/user-guide/advanced-guide/pipelining-features/schedule-pipeline-runs)
{% endhint %}


## How to deploy it

You don't need to do anything special to deploy the SkyPilot VM Orchestrator. As the SkyPilot integration
itself takes care of provisioning VMs, you can simply use the orchestrator as you would any other ZenML
orchestrator. However, you will need to ensure that you have the appropriate permissions to provision VMs
on your cloud provider of choice and to configure your SkyPilot orchestrator accordingly using the [service
connectors](https://docs.zenml.io/stacks-and-components/auth-management) feature.

{% hint style="info" %}
The SkyPilot VM Orchestrator is currently only supported on AWS, GCP, and Azure.
{% endhint %}


## How to use it

To use the SkyPilot VM Orchestrator, you need:

* One of the SkyPilot integrations installed. You can install the SkyPilot integration for your cloud provider of choice using the following command:
  ```shell
    # For AWS
    pip install zenml[connectors-gcp]
    zenml integration install aws vm_aws 

    # for GCP
    pip install zenml[connectors-gcp]
    zenml integration install gcp vm_gcp # for GCP

    # for Azure
    pip install zenml[connectors-azure]
    zenml integration install azure vm_azure # for Azure
  ```
* [Docker](https://www.docker.com) installed and running.
* A [remote artifact store](../artifact-stores/artifact-stores.md) as part of your stack.
* A [remote container registry](../container-registries/container-registries.md) as part of your stack.
* A [remote ZenML deployment](/docs/book/deploying-zenml/zenml-self-hosted/zenml-self-hosted.md) as part of your stack.
* The appropriate permissions to provision VMs on your cloud provider of choice.

### Configure Service Connector with the SkyPilot VM Orchestrator.

To provision VMs on AWS, your VM Orchestrator stack component needs to be configured to authenticate with cloud provider.
We recommend using one of available [Service Connector](https://docs.zenml.io/stacks-and-components/auth-management/service-connectors-guide) 
for this purpose. For this example, we will use the [AWS Service Connector](https://docs.zenml.io/stacks-and-components/auth-management/aws-service-connector)
To configure the AWS Service Connector, you need to register a new service connector using the
following command:

```
zenml service-connector list-types --type aws
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━┯━━━━━━━┯━━━━━━━━┓
┃         NAME          │ TYPE   │ RESOURCE TYPES        │ AUTH METHODS     │ LOCAL │ REMOTE ┃
┠───────────────────────┼────────┼───────────────────────┼──────────────────┼───────┼────────┨
┃ AWS Service Connector │ 🔶 aws │ 🔶 aws-generic        │ implicit         │ ✅    │ ➖     ┃
┃                       │        │ 📦 s3-bucket          │ secret-key       │       │        ┃
┃                       │        │ 🌀 kubernetes-cluster │ sts-token        │       │        ┃
┃                       │        │ 🐳 docker-registry    │ iam-role         │       │        ┃
┃                       │        │                       │ session-token    │       │        ┃
┃                       │        │                       │ federation-token │       │        ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━┷━━━━━━━┷━━━━━━━━┛
zenml service-connector register aws-skypilot-vm -t aws --auto-configure 

```

This will automatically configure the service connector with the appropriate credentials and permissions to
provision VMs on AWS. You can then use the service connector to configure your registered VM Orchestrator stack component
using the following command:

```shell
# Register the orchestrator
zenml orchestrator register <ORCHESTRATOR_NAME> --flavor vm_aws
# Connect the orchestrator to the service connector
zenml orchestrator connect <ORCHESTRATOR_NAME> --connector aws-skypilot-vm

# Register and activate a stack with the new orchestrator
zenml stack register <STACK_NAME> -o <ORCHESTRATOR_NAME> ... --set
```


#### Additional Configuration

For additional configuration of the Skypilot orchestrator, you can pass `SkypilotBaseOrchestratorSettings` which allows you to configure (among others) the following attributes:

* `instance_type`: The instance type to use.
* `cpus`: The number of CPUs required for the task. If a string, must be a string of the form `'2'` or `'2+'`, where the `+` indicates that the task requires at least 2 CPUs.
* `memory`: The amount of memory in GiB required. If a string, must be a string of the form `'16'` or `'16+'`, where the `+` indicates that the task requires at least 16 GB of memory.
* `accelerators`: The accelerators required. If a string, must be a string of the form `'V100'` or `'V100:2'`, where the `:2` indicates that the task requires 2 V100 GPUs. If a dict, must be a dict of the form `{'V100': 2}` or `{'tpu-v2-8': 1}`.
* `accelerator_args`: Accelerator-specific arguments. For example, `{'tpu_vm': True, 'runtime_version': 'tpu-vm-base'}` for TPUs.
* `use_spot`: Whether to use spot instances. If None, defaults to False.
* `spot_recovery`: The spot recovery strategy to use for the managed spot to recover the cluster from preemption.
* `region`: The region to use.
* `zone`: The zone to use.
* `image_id`: The image ID to use. If a string, must be a string of the image id from the cloud, such as AWS: `'ami-1234567890abcdef0'`, GCP: `'projects/my-project-id/global/images/my-image-name'`; Or, a image tag provided by SkyPilot, such as AWS: `'skypilot:gpu-ubuntu-2004'`. If a dict, must be a dict mapping from region to image ID.
* `disk_size`: The size of the OS disk in GiB.
* `disk_tier`: The disk performance tier to use. If None, defaults to `'medium'`.
* `cluster_name`: Name of the cluster to create/reuse. If None, auto-generate a name.
* `retry_until_up`: Whether to retry launching the cluster until it is up.
* `idle_minutes_to_autostop`: Automatically stop the cluster after this many minutes of idleness, i.e., no running or pending jobs in the cluster's job queue. Idleness gets reset whenever setting-up/running/pending jobs are found in the job queue. Setting this flag is equivalent to running `sky.launch(..., detach_run=True, ...)` and then `sky.autostop(idle_minutes=<minutes>)`. If not set, the cluster will not be autostopped.
* `down`: Tear down the cluster after all jobs finish (successfully or abnormally). If `idle_minutes_to_autostop` is also set, the cluster will be torn down after the specified idle time. Note that if errors occur during provisioning/data syncing/setting up, the cluster will not be torn down for debugging purposes.
* `stream_logs`: If True, show the logs in the terminal.

```python
from zenml.integrations.skypilot.flavors.skypilot_orchestrator_flavor import SkypilotBaseOrchestratorSettings

skypilot_settings = SkypilotBaseOrchestratorSettings(
    instance_type="m5.large",
    cpus="2",
    memory="16",
    accelerators="V100:2",
    accelerator_args={"tpu_vm": True, "runtime_version": "tpu-vm-base"},
    use_spot=True,
    spot_recovery="recovery_strategy",
    region="us-west1",
    zone="us-west1-a",
    image_id="ami-1234567890abcdef0",
    disk_size=100,
    disk_tier="high",
    cluster_name="my_cluster",
    retry_until_up=True,
    idle_minutes_to_autostop=60,
    down=True,
    stream_logs=True
)


@pipeline(
    settings={
        "orchestrator.skypilot": skypilot_settings
    }
)
```

Check out
the [SDK docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-kubeflow/#zenml.integrations.kubeflow.flavors.kubeflow\_orchestrator\_flavor.KubeflowOrchestratorSettings)
for a full list of available attributes and [this docs page](/docs/book/user-guide/advanced-guide/pipelining-features/configure-steps-pipelines.md) for more
information on how to specify settings.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
