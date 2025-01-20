---
description: Orchestrating your pipelines to run on HyperAI.ai instances.
---

# HyperAI Orchestrator

[HyperAI](https://www.hyperai.ai) is a cutting-edge cloud compute platform designed to make AI accessible for everyone. The HyperAI orchestrator is an [orchestrator](./orchestrators.md) flavor that allows you to easily deploy your pipelines on HyperAI instances.

{% hint style="warning" %}
This component is only meant to be used within the context of a [remote ZenML deployment scenario](../../getting-started/deploying-zenml/README.md). Usage with a local ZenML deployment may lead to unexpected behavior!
{% endhint %}

### When to use it

You should use the HyperAI orchestrator if:

* you're looking for a managed solution for running your pipelines.
* you're a HyperAI customer.

### Prerequisites

You will need to do the following to start using the HyperAI orchestrator:

* Have a running HyperAI instance. It must be accessible from the internet (or at least from the IP addresses of your ZenML users) and allow SSH key based access (passwords are not supported).
* Ensure that a recent version of Docker is installed. This version must include Docker Compose, meaning that the command `docker compose` works.
* Ensure that the appropriate [NVIDIA Driver](https://www.nvidia.com/en-us/drivers/unix/) is installed on the HyperAI instance (if not already installed by the HyperAI team).
* Ensure that the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) is installed and configured on the HyperAI instance.

Note that it is possible to omit installing the NVIDIA Driver and NVIDIA Container Toolkit. However, you will then be unable to use the GPU from within your ZenML pipeline. Additionally, you will then need to disable GPU access within the container when configuring the Orchestrator component, or the pipeline will not start correctly.

## How it works

The HyperAI orchestrator works with Docker Compose, which can be used to construct machine learning pipelines. Under the hood, it creates a Docker Compose file which it then deploys and executes on the configured HyperAI instance. For each ZenML pipeline step, it creates a service in this file. It uses the `service_completed_successfully` condition to ensure that pipeline steps will only run if their connected upstream steps have successfully finished.

If configured for it, the HyperAI orchestrator will connect the HyperAI instance to the stack's container registry to ensure a smooth transfer of Docker images.

### Scheduled pipelines

[Scheduled pipelines](../../how-to/pipeline-development/build-pipelines/schedule-a-pipeline.md) are supported by the HyperAI orchestrator. Currently, the HyperAI orchestrator supports the following inputs to `Schedule`:

* Cron expressions via `cron_expression`. When pipeline runs are scheduled, they are added as a crontab entry on the HyperAI instance. Use this when you want pipelines to run in intervals. Using cron expressions assumes that `crontab` is available on your instance and that its daemon is running.
* Scheduled runs via `run_once_start_time`. When pipeline runs are scheduled this way, they are added as an `at` entry on the HyperAI instance. Use this when you want pipelines to run just once and at a specified time. This assumes that `at` is available on your instance.

### How to deploy it

To use the HyperAI orchestrator, you must configure a HyperAI Service Connector in ZenML and link it to the HyperAI orchestrator component. The service connector contains credentials with which ZenML connects to the HyperAI instance.

Additionally, the HyperAI orchestrator must be used in a stack that contains a container registry and an image builder.

### How to use it

To use the HyperAI orchestrator, we must configure a HyperAI Service Connector first using one of its supported authentication methods. For example, for authentication with an RSA-based key, create the service connector as follows:

```shell
zenml service-connector register <SERVICE_CONNECTOR_NAME> --type=hyperai --auth-method=rsa-key --base64_ssh_key=<BASE64_SSH_KEY> --hostnames=<INSTANCE_1>,<INSTANCE_2>,..,<INSTANCE_N> --username=<INSTANCE_USERNAME>
```

Hostnames are either DNS resolvable names or IP addresses.

For example, if you have two servers - one at `1.2.3.4` and another at `4.3.2.1`, you could provide them as `--hostnames=1.2.3.4,4.3.2.1`.

Optionally, it is possible to provide a passphrase for the key (`--ssh_passphrase`).

Following registering the service connector, we can register the orchestrator and use it in our active stack:

```shell
zenml orchestrator register <ORCHESTRATOR_NAME> --flavor=hyperai

# Register and activate a stack with the new orchestrator
zenml stack register <STACK_NAME> -o <ORCHESTRATOR_NAME> ... --set
```

You can now run any ZenML pipeline using the HyperAI orchestrator:

```shell
python file_that_runs_a_zenml_pipeline.py
```

#### Enabling CUDA for GPU-backed hardware

Note that if you wish to use this orchestrator to run steps on a GPU, you will need to follow [the instructions on this page](../../how-to/pipeline-development/training-with-gpus/README.md) to ensure that it works. It requires adding some extra settings customization and is essential to enable CUDA for the GPU to give its full acceleration.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
