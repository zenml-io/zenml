---
description: Orchestrating your pipelines to run on VMs using SkyPilot.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# SkyPilot VM Orchestrator

The SkyPilot VM Orchestrator is an integration provided by ZenML that allows you to
provision and manage virtual machines (VMs) on any cloud provider supported by the [SkyPilot framework](https://skypilot.readthedocs.io/en/latest/index.html).
This integration is designed to simplify the process of running machine learning workloads
on the cloud, offering cost savings, high GPU availability, and managed execution, We recommend
using the SkyPilot VM Orchestrator if you need access to GPUs for your workloads, but don't want
to deal with the complexities of managing cloud infrastructure or expensive managed solutions.

{% hint style="warning" %}
This component is only meant to be used within the context of
a [remote ZenML deployment scenario](/docs/book/deploying-zenml/zenml-self-hosted/zenml-self-hosted.md).
Usage with a local ZenML deployment may lead to unexpected behavior!
{% endhint %}

{% hint style="warning" %}
SkyPilot VM Orchestrator is currently supported only for Python 3.8 and 3.9.
{% endhint %}

## When to use it

You should use the SkyPilot VM Orchestrator if:

* you want to maximize cost savings by leveraging spot VMs and auto-picking the cheapest VM/zone/region/cloud.
* you want to ensure high GPU availability by provisioning VMs in all zones/regions/clouds you have access to.
* you don't need a built-in UI of the orchestrator. (You can still use ZenML's Dashboard to view and monitor your pipelines/artifacts.)
* you're not willing to maintain Kubernetes-based solutions or pay for managed solutions like [Sagemaker](sagemaker.md).


## How it works


The orchestrator leverages the SkyPilot framework to handle the provisioning and scaling of VMs.
It automatically manages the process of launching VMs for your pipelines, with support for both
on-demand and managed spot VMs. While you can select the VM type you want to use, the orchestrator
also includes an optimizer that automatically selects the cheapest VM/zone/region/cloud for your workloads.
Finally, the orchestrator includes an autostop feature that cleans up idle clusters, preventing unnecessary cloud costs.

{% hint style="warning" %}
The SkyPilot VM Orchestrator does not currently support the ability to [schedule pipelines runs](/docs/book/user-guide/advanced-guide/pipelining-features/schedule-pipeline-runs.md)
{% endhint %}


## How to deploy it

You don't need to do anything special to deploy the SkyPilot VM Orchestrator. As the SkyPilot integration
itself takes care of provisioning VMs, you can simply use the orchestrator as you would any other ZenML
orchestrator. However, you will need to ensure that you have the appropriate permissions to provision VMs
on your cloud provider of choice and to configure your SkyPilot orchestrator accordingly using the [service
connectors](../../../stacks-and-components/auth-management/service-connectors-guide.md) feature.

{% hint style="info" %}
The SkyPilot VM Orchestrator currently only supports the AWS, GCP, and Azure cloud platforms.
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
* A [service connector](../../../stacks-and-components/auth-management/service-connectors-guide.md) configured to authenticate with your cloud provider of choice.


{% tabs %}
{% tab title="AWS" %}

We need first to install the SkyPilot integration for AWS and the AWS connectors extra, using the following two commands:

  ```shell
    pip install zenml[connectors-aws]
    zenml integration install aws vm_aws 
  ```

To provision VMs on AWS, your VM Orchestrator stack component needs to be configured to authenticate with [AWS Service Connector](../../../stacks-and-components/auth-management/aws-service-connector.md).
To configure the AWS Service Connector, you need to register a new service connector, but first let's check the available service connector types using the following command:

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
```

For this example we will configure a service connector using the `iam-role` auth method. But before we can do that, we recommend you to create a new AWS profile that will be used by the service connector. Once we have created the profile, we can register a new service connector using the following command:

```shell
AWS_PROFILE=connectors zenml service-connector register aws-skypilot-vm --type aws --region=us-east-1 --auto-configure
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
{% endtab %}

{% tab title="GCP" %}

We need first to install the SkyPilot integration for GCP and the GCP extra for ZenML, using the following two commands:

  ```shell
    pip install zenml[connectors-gcp]
    zenml integration install gcp vm_gcp 
  ```

To provision VMs on GCP, your VM Orchestrator stack component needs to be configured to authenticate with [GCP Service Connector](../../../stacks-and-components/auth-management/gcp-service-connector.md)

To configure the GCP Service Connector, you need to register a new service connector, but first let's check the available service connectors types using the following command:

```
zenml service-connector list-types --type gcp
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━┯━━━━━━━┯━━━━━━━━┓
┃         NAME          │ TYPE   │ RESOURCE TYPES        │ AUTH METHODS    │ LOCAL │ REMOTE ┃
┠───────────────────────┼────────┼───────────────────────┼─────────────────┼───────┼────────┨
┃ GCP Service Connector │ 🔵 gcp │ 🔵 gcp-generic        │ implicit        │ ✅    │ ➖     ┃
┃                       │        │ 📦 gcs-bucket         │ user-account    │       │        ┃
┃                       │        │ 🌀 kubernetes-cluster │ service-account │       │        ┃
┃                       │        │ 🐳 docker-registry    │ oauth2-token    │       │        ┃
┃                       │        │                       │ impersonation   │       │        ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━┷━━━━━━━┷━━━━━━━━┛
```

For this example we will configure a service connector using the `user-account` auth method. But before we can do that, we need to
login to GCP using the following command:

```shell
 gcloud auth application-default login 
```

This will open a browser window and ask you to login to your GCP account. Once you have logged in, you can register a new service connector using the
following command:

```shell
# We want to use --auto-configure to automatically configure the service connector with the appropriate credentials and permissions to provision VMs on GCP.
zenml service-connector register gcp-skypilot-vm -t gcp --auth-method user-account --auto-configure 
# using generic resource type requires disabling the generation of temporary tokens
zenml service-connector update gcp-skypilot-vm --generate_temporary_tokens=False
```

This will automatically configure the service connector with the appropriate credentials and permissions to
provision VMs on GCP. You can then use the service connector to configure your registered VM Orchestrator stack component
using the following commands:

```shell
# Register the orchestrator
zenml orchestrator register <ORCHESTRATOR_NAME> --flavor vm_gcp
# Connect the orchestrator to the service connector
zenml orchestrator connect <ORCHESTRATOR_NAME> --connector gcp-skypilot-vm

# Register and activate a stack with the new orchestrator
zenml stack register <STACK_NAME> -o <ORCHESTRATOR_NAME> ... --set
```
{% endtab %}

{% tab title="Azure" %}

We need first to install the SkyPilot integration for Azure and the Azure extra for ZenML, using the following two commands

  ```shell
    pip install zenml[connectors-azure]
    zenml integration install azure vm_azure 
  ```

To provision VMs on Azure, your VM Orchestrator stack component needs to be configured to authenticate with [Azure Service Connector](../../../stacks-and-components/auth-management/azure-service-connector.md)

To configure the Azure Service Connector, you need to register a new service connector, but first let's check the available service connectors types using the following command:


```
zenml service-connector list-types --type azure
┏━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━┯━━━━━━━┯━━━━━━━━┓
┃          NAME           │ TYPE      │ RESOURCE TYPES        │ AUTH METHODS      │ LOCAL │ REMOTE ┃
┠─────────────────────────┼───────────┼───────────────────────┼───────────────────┼───────┼────────┨
┃ Azure Service Connector │ 🇦  azure │ 🇦  azure-generic     │ implicit          │ ✅    │ ➖     ┃
┃                         │           │ 📦 blob-container     │ service-principal │       │        ┃
┃                         │           │ 🌀 kubernetes-cluster │ access-token      │       │        ┃
┃                         │           │ 🐳 docker-registry    │                   │       │        ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━┷━━━━━━━┷━━━━━━━━┛
zenml service-connector register azure-skypilot-vm -t azure --auth-method access-token --auto-configure
```

This will automatically configure the service connector with the appropriate credentials and permissions to
provision VMs on Azure. You can then use the service connector to configure your registered VM Orchestrator stack component
using the following commands:

```shell
# Register the orchestrator
zenml orchestrator register <ORCHESTRATOR_NAME> --flavor vm_azure
# Connect the orchestrator to the service connector
zenml orchestrator connect <ORCHESTRATOR_NAME> --connector azure-skypilot-vm

# Register and activate a stack with the new orchestrator
zenml stack register <STACK_NAME> -o <ORCHESTRATOR_NAME> ... --set
```
{% endtab %}
{% endtabs %}

#### Additional Configuration

For additional configuration of the Skypilot orchestrator, you can pass `SkypilotBaseOrchestratorSettings` which allows you to configure (among others) the following attributes:

* `instance_type`: The instance type to use.
* `cpus`: The number of CPUs required for the task. If a string, must be a string of the form `'2'` or `'2+'`, where the `+` indicates that the task requires at least 2 CPUs.
* `memory`: The amount of memory in GiB required. If a string, must be a string of the form `'16'` or `'16+'`, where the `+` indicates that the task requires at least 16 GB of memory.
* `accelerators`: The accelerators required. If a string, must be a string of the form `'V100'` or `'V100:2'`, where the `:2` indicates that the task requires 2 V100 GPUs. If a dict, must be a dict of the form `{'V100': 2}` or `{'tpu-v2-8': 1}`.
* `accelerator_args`: Accelerator-specific arguments. For example, `{'tpu_vm': True, 'runtime_version': 'tpu-vm-base'}` for TPUs.
* `use_spot`: Whether to use spot instances. If None, defaults to False.
* `spot_recovery`: The spot recovery strategy to use for the managed spot to recover the cluster from preemption. Read more about the available strategies [here](https://skypilot.readthedocs.io/en/latest/reference/api.html?highlight=instance_type#resources)
* `region`: The cloud region to use.
* `zone`: The cloud zone to use within the region.
* `image_id`: The image ID to use. If a string, must be a string of the image id from the cloud, such as AWS: `'ami-1234567890abcdef0'`, GCP: `'projects/my-project-id/global/images/my-image-name'`; Or, a image tag provided by SkyPilot, such as AWS: `'skypilot:gpu-ubuntu-2004'`. If a dict, must be a dict mapping from region to image ID.
* `disk_size`: The size of the OS disk in GiB.
* `disk_tier`: The disk performance tier to use. If None, defaults to `'medium'`.
* `cluster_name`: Name of the cluster to create/reuse. If None, auto-generate a name. SkyPilot uses term `cluster` to refer to a group or a single VM that are provisioned to execute the task. The cluster name is used to identify the cluster and to determine whether to reuse an existing cluster or create a new one.
* `retry_until_up`: Whether to retry launching the cluster until it is up.
* `idle_minutes_to_autostop`: Automatically stop the cluster after this many minutes of idleness, i.e., no running or pending jobs in the cluster's job queue. Idleness gets reset whenever setting-up/running/pending jobs are found in the job queue. Setting this flag is equivalent to running `sky.launch(..., detach_run=True, ...)` and then `sky.autostop(idle_minutes=<minutes>)`. If not set, the cluster will not be autostopped.
* `down`: Tear down the cluster after all jobs finish (successfully or abnormally). If `idle_minutes_to_autostop` is also set, the cluster will be torn down after the specified idle time. Note that if errors occur during provisioning/data syncing/setting up, the cluster will not be torn down for debugging purposes.
* `stream_logs`: If True, show the logs in the terminal as they are generated while the cluster is running.

**Code Example:**

```python
from zenml.integrations.skypilot.flavors.skypilot_orchestrator_flavor import SkypilotBaseOrchestratorSettings

skypilot_settings = SkypilotBaseOrchestratorSettings(
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
the [SDK docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-skypilot/#zenml.integrations.skypilot.flavors.skypilot\_orchestrator\_base\_vm\_flavor.SkypilotBaseOrchestratorSettings)
for a full list of available attributes and [this docs page](/docs/book/user-guide/advanced-guide/pipelining-features/configure-steps-pipelines.md) for more
information on how to specify settings.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
