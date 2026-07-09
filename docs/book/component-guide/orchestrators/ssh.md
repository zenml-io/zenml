---
description: Orchestrating your pipelines on a remote host via SSH and Docker.
---

# SSH Orchestrator

The SSH orchestrator is an [orchestrator](./) flavor that runs your pipelines on a remote Linux host over SSH, using Docker Compose. It is a generic, vendor-neutral alternative to managed orchestrators: if you have a machine reachable over SSH that can run Docker, you can use it as a ZenML orchestrator.

It is the spiritual successor to the [HyperAI orchestrator](hyperai.md) — it uses the same Compose-based execution model but is not tied to any particular cloud provider, and it adds support for [dynamic pipelines](https://docs.zenml.io/how-to/steps-pipelines/dynamic_pipelines).

{% hint style="info" %}
The SSH orchestrator supersedes the [HyperAI orchestrator](hyperai.md), which is now deprecated. New stacks should use the SSH orchestrator; existing HyperAI users can migrate by registering an `ssh` orchestrator pointed at the same host (see [Migrating from HyperAI](#migrating-from-hyperai) below).
{% endhint %}

{% hint style="warning" %}
This component is only meant to be used within the context of a [remote ZenML deployment scenario](https://docs.zenml.io/getting-started/deploying-zenml/). Usage with a local ZenML deployment may lead to unexpected behavior!
{% endhint %}

### When to use it

You should use the SSH orchestrator if:

* you have a **dedicated remote machine** (e.g. a GPU workstation or on-prem server) reachable over SSH and want to run full pipelines on it.
* you want a simple, self-hosted orchestrator without Kubernetes or a cloud-managed service.
* you are migrating away from the deprecated HyperAI orchestrator.

If you only want to offload *individual* compute-heavy steps to a remote host while keeping a different orchestrator, consider the sibling [SSH step operator](../step-operators/ssh.md) instead. The two share the same connection layer and can target the same host.

### Prerequisites

You will need the following to use the SSH orchestrator:

* A remote Linux host reachable over SSH from the machine submitting the pipeline, with **SSH key-based** access (passwords are not supported).
* A recent version of **Docker** including Docker Compose (the `docker compose` command must work) and the SSH user must be able to run it (typically a member of the `docker` group).
* For GPU pipelines: the appropriate [NVIDIA Driver](https://www.nvidia.com/en-us/drivers/unix/) and the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) installed on the host. If GPUs are not available, set `gpu_enabled=False` (or per step via settings), otherwise the pipeline will not start correctly.

## How it works

The SSH orchestrator connects to the remote host with [paramiko](https://www.paramiko.org/), writes a Docker Compose file into a per-run directory under `remote_workdir`, and launches it with `docker compose up`. It has two execution paths:

* **Static pipelines** — one Compose service per step, wired together with `depends_on` (`service_completed_successfully`) so a step only runs once its upstream steps finish. The remote `docker compose up` runs the whole DAG. This mirrors the HyperAI execution model.
* **Dynamic pipelines** — a single Compose service runs the *orchestrator image*, which executes ZenML's dynamic runner on the host. That runner launches each isolated step as its own OS **subprocess** (not a thread) so steps are independently accounted and can be preempted — required for resource pools and fail-fast execution.

If `authenticate_docker` is enabled, the orchestrator runs `docker login` on the remote host using the submitted stack's container registry credentials before launching, so private images can be pulled.

{% hint style="info" %}
The SSH orchestrator does not manage schedules. To run a pipeline on a schedule, trigger it directly from your own cron job or CI; submitting a pipeline with a ZenML schedule is rejected with a clear error.
{% endhint %}

### How to deploy it

The SSH orchestrator connects to an existing host; it does not provision infrastructure. Beyond the [prerequisites](#prerequisites) above, the orchestrator must be used in a stack that contains a **container registry** and an **image builder**. SSH credentials are configured directly on the orchestrator.

### How to use it

Install the ZenML `ssh` integration:

```shell
zenml integration install ssh
```

Register the orchestrator with the connection details for your host and use it in your active stack:

```shell
zenml orchestrator register <ORCHESTRATOR_NAME> \
    --flavor=ssh \
    --hostname=<HOST_OR_IP> \
    --username=<SSH_USERNAME> \
    --ssh_key_path=<PATH_TO_PRIVATE_KEY>

# Register and activate a stack with the new orchestrator
zenml stack register <STACK_NAME> -o <ORCHESTRATOR_NAME> ... --set
```

Instead of `ssh_key_path` (a path on the submitting machine) you can store the key content in a [ZenML secret](https://docs.zenml.io/getting-started/deploying-zenml/secret-management) and reference it via `ssh_private_key` (and `ssh_key_passphrase` if the key is encrypted).

You can now run any ZenML pipeline using the SSH orchestrator:

```shell
python file_that_runs_a_zenml_pipeline.py
```

#### Configuration options

Key configuration fields (set at registration time):

* `hostname`, `port`, `username` — how to reach the host.
* `ssh_key_path` / `ssh_private_key` / `ssh_key_passphrase` — key-based authentication.
* `verify_host_key` / `known_hosts_path` — host-key verification (on by default).
* `remote_workdir` — base directory on the host for per-run files (default `/tmp/zenml-ssh`).
* `docker_binary` — path to the Docker binary on the host (default `docker`).
* `authenticate_docker` — run `docker login` on the host before launching (default `False`).
* `cleanup_old_files` — remove run directories older than seven days before each launch (default `True`).
* `gpu_enabled` — request all NVIDIA GPUs for step containers. This is also a per-step setting, so you can mix CPU and GPU steps in one pipeline.

Bind mounts can be configured per pipeline or per step via settings:

```python
from zenml.integrations.ssh.flavors.ssh_orchestrator_flavor import (
    SSHOrchestratorSettings,
)

settings = SSHOrchestratorSettings(
    mounts={"/data/datasets": "/datasets"},
    gpu_enabled=False,
)
```

#### Enabling CUDA for GPU-backed hardware

If you wish to run steps on a GPU, follow [the instructions on this page](https://docs.zenml.io/user-guides/tutorial/distributed-training/) to ensure CUDA is enabled inside the container. This requires some extra settings customization and is essential to give the GPU its full acceleration.

### Migrating from HyperAI

The HyperAI orchestrator is deprecated in favor of the SSH orchestrator. Since both connect over SSH and run Docker Compose on the host, migration is straightforward: register an `ssh` orchestrator pointed at the same host and SSH credentials, then switch your stack to it.

```shell
zenml orchestrator register <ORCHESTRATOR_NAME> \
    --flavor=ssh \
    --hostname=<SAME_HOST> \
    --username=<SAME_USERNAME> \
    --ssh_key_path=<PATH_TO_PRIVATE_KEY>

zenml stack update <STACK_NAME> -o <ORCHESTRATOR_NAME>
```

The main difference from HyperAI is that the SSH orchestrator uses the generic SSH integration and additionally supports dynamic pipelines.
