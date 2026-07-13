---
description: Executing individual ZenML steps on Slurm clusters.
---

# Slurm Step Operator

The Slurm step operator is a [step operator](./) flavor that runs selected ZenML
steps as Slurm batch jobs on an existing HPC cluster. It is useful when most of
your pipeline can run on another orchestrator, but one or more compute-heavy
steps need Slurm-managed CPU, memory, or GPU resources.

{% hint style="info" %}
The Slurm step operator does not orchestrate dynamic pipelines. For full
pipeline execution, including dynamic pipelines, use the
[Slurm orchestrator](../orchestrators/slurm.md).
{% endhint %}

{% hint style="warning" %}
The Slurm step operator runs a single containerized job per selected step. It
does not provide first-class Slurm arrays, MPI or multi-node helpers,
`slurmrestd`, accounting-based reconciliation, or scheduling support.
{% endhint %}

### When to use it

You should use the Slurm step operator if:

* your organization already has a Slurm cluster.
* only selected steps need HPC resources.
* compute nodes can pull the step image from your container registry.
* compute nodes can read and write artifacts through your remote artifact store.
* a shared `workdir` path is visible from the Slurm submission host and compute
  nodes.

If you want every step in the pipeline to run as a Slurm job, use the
[Slurm orchestrator](../orchestrators/slurm.md) instead.

### Prerequisites

To use the Slurm step operator, you need:

* The ZenML `slurm` integration installed.
* Access to a Slurm submission host with `sbatch`, `squeue`, `scontrol`, and
  `scancel` available.
* A shared `workdir` path visible from both the submission host and compute
  nodes.
* A remote artifact store reachable from compute nodes.
* A remote container registry and image builder.
* One supported compute-node container runtime:
  * `apptainer` or `singularity`.
  * `pyxis`.
  * `docker`, only where compute nodes expose a Docker daemon.

### How it works

When a step uses the Slurm step operator, ZenML builds and pushes the step image
through the active stack's image builder and container registry. The step
operator then connects to the Slurm submission host, stages a job script and
owner-only environment file in `workdir`, and submits the job with `sbatch`.

The job script runs the step container on the compute node and writes an exit
sentinel when it finishes. ZenML polls Slurm with `squeue`/`scontrol` and reads
the sentinel file after the job leaves the queue, so it does not require Slurm
accounting (`sacct`) to be enabled.

### How to use it

Install the Slurm integration:

```shell
zenml integration install slurm
```

Register the step operator for a remote login node:

```shell
zenml step-operator register <STEP_OPERATOR_NAME> \
    --flavor=slurm \
    --transport=ssh \
    --hostname=<LOGIN_NODE_HOSTNAME> \
    --username=<SSH_USERNAME> \
    --ssh_key_path=<PATH_TO_PRIVATE_KEY> \
    --workdir=/shared/zenml-runs \
    --container_runtime=apptainer \
    --partition=<PARTITION> \
    --account=<SLURM_ACCOUNT>
```

For a client or orchestrator process that already runs on a Slurm login node,
use local transport:

```shell
zenml step-operator register <STEP_OPERATOR_NAME> \
    --flavor=slurm \
    --transport=local \
    --workdir=/shared/zenml-runs \
    --container_runtime=apptainer
```

Attach the step operator to a stack that also includes a remote artifact store,
a container registry, and an image builder:

```shell
zenml stack update \
    -s <STEP_OPERATOR_NAME> \
    -a <REMOTE_ARTIFACT_STORE> \
    -c <CONTAINER_REGISTRY> \
    -i <IMAGE_BUILDER>
```

Use the step operator on selected steps:

```python
from zenml import step


@step(step_operator="<STEP_OPERATOR_NAME>")
def train_model() -> None:
    ...
```

### Configuration options

Key registration-time options:

| Option | Description |
|--------|-------------|
| `transport` | `ssh` to connect to a remote login node, or `local` to run Slurm commands on the current machine. |
| `hostname`, `username`, `port` | SSH connection details. Required for `transport=ssh`. |
| `ssh_key_path` | Path to a private key on the machine that submits the step. |
| `ssh_private_key`, `ssh_key_passphrase` | Private key content and optional passphrase. Prefer ZenML secrets for these values when the submitting process runs remotely. |
| `verify_host_key`, `known_hosts_path` | Host-key verification settings inherited from the SSH integration. Verification is enabled by default. |
| `workdir` | Shared directory used to stage per-step Slurm files. Must be visible from the submission host and compute nodes. |
| `container_runtime` | One of `apptainer`, `singularity`, `pyxis`, or `docker`. |
| `partition`, `time_limit`, `account`, `qos` | Common Slurm scheduling directives mapped to `#SBATCH` lines. |
| `extra_sbatch_directives` | Additional raw `#SBATCH` options such as `--constraint=a100`, `--reservation=<name>`, or `--exclusive`. |
| `container_mounts` | Host-path to container-path mounts, for example `{'/scratch/user': '/scratch'}`. |
| `container_run_args` | Additional arguments passed to the selected container runtime. |

You can override Slurm job settings per step:

```python
from zenml import step
from zenml.integrations.slurm.flavors.slurm_step_operator_flavor import (
    SlurmStepOperatorSettings,
)

slurm_settings = SlurmStepOperatorSettings(
    partition="gpu",
    time_limit="4:00:00",
    account="ml-research",
    extra_sbatch_directives=["--constraint=a100"],
    container_mounts={"/scratch/$USER": "/scratch"},
)


@step(
    step_operator="<STEP_OPERATOR_NAME>",
    settings={"step_operator": slurm_settings},
)
def train_model() -> None:
    ...
```

ZenML maps standard step resource settings to Slurm directives:

* `cpu_count` becomes `--cpus-per-task`.
* memory becomes `--mem`.
* `gpu_count` becomes `--gres=gpu:<count>`.

### Container runtimes

The selected `container_runtime` controls how the ZenML image is executed on the
compute node:

* `apptainer` and `singularity` run `apptainer exec` or `singularity exec` with
  `docker://<image>`.
* `pyxis` uses `srun --container-image=<image>` and passes selected environment
  variables through `--container-env`.
* `docker` uses `docker run --rm`, which only works on clusters where Docker is
  available and permitted on compute nodes.

Private registry credentials, when configured on the active container registry,
are staged as owner-only files and consumed by the selected runtime.

### Security and cleanup

The step operator writes the environment file with `0600` permissions in an
owner-only staging directory. Secrets are passed through files or environment
variable names, not as visible command-line values. The generated Slurm script
installs an `EXIT` trap that writes the step exit code and removes credential
files when the job finishes.

If a step is cancelled while still pending, the step operator explicitly removes
known sensitive files because the job script may never start and therefore may
never run its `EXIT` trap.

### Limitations

The Slurm step operator is intentionally narrow:

* It is a per-step offload mechanism, not a dynamic pipeline engine.
* It requires a remote artifact store and remote container registry.
* It does not manage schedules.
* It does not provide first-class helpers for MPI, multi-node training, Slurm
  arrays, pre-staged SIF images, or Slurm accounting.
* Site-specific requirements should be passed through
  `extra_sbatch_directives` and validated on your cluster.

Check out the [SDK docs](https://sdkdocs.zenml.io/latest/) for the full API
reference.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
