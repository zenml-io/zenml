---
description: Orchestrating ZenML pipelines on Slurm clusters.
---

# Slurm Orchestrator

The Slurm orchestrator is an [orchestrator](./) flavor that submits ZenML
pipeline runs to an existing [Slurm](https://slurm.schedmd.com/) cluster. Each
pipeline step runs as a Slurm batch job, using the standard ZenML container image
for that step and a container runtime available on the compute nodes.

Use this orchestrator when you already have an HPC cluster managed by Slurm and
want ZenML to submit whole pipeline runs to it. If you only want to offload a
few individual steps while another orchestrator runs the rest of the pipeline,
use the [Slurm step operator](../step-operators/slurm.md) instead.

{% hint style="warning" %}
The Slurm integration targets containerized, one-Slurm-job-per-step workloads
with a shared POSIX staging directory. It does not currently provide
first-class Slurm arrays, MPI or multi-node job helpers, `slurmrestd`,
accounting-based reconciliation, or scheduling support.
{% endhint %}

### When to use it

You should use the Slurm orchestrator if:

* you have an existing Slurm cluster and want to run complete ZenML pipelines on
  it.
* your cluster can pull container images through Apptainer, Singularity, Pyxis,
  or Docker.
* the Slurm login node and compute nodes can access the same staging directory
  configured as `workdir`.
* your pipeline artifacts live in a remote artifact store that compute nodes can
  reach.

Use another orchestrator if your cluster cannot run container images, if compute
nodes cannot reach your artifact store, or if you need native Slurm features
that are not exposed by this integration yet.

### Prerequisites

To use the Slurm orchestrator, you need:

* The ZenML `slurm` integration installed.
* Access to a Slurm submission host with `sbatch`, `squeue`, `scontrol`, and
  `scancel` available.
* A shared `workdir` path visible from both the submission host and compute
  nodes. ZenML stores job scripts, owner-only env files, output logs, and
  completion sentinels there.
* A remote artifact store, such as S3, GCS, Azure Blob Storage, or another
  artifact store reachable from the compute nodes.
* A remote container registry and an image builder so ZenML can build and push
  the step images that Slurm jobs pull.
* One supported compute-node container runtime:
  * `apptainer` or `singularity`, using `docker://<image>` image references.
  * `pyxis`, using `srun --container-image`.
  * `docker`, only on clusters where compute nodes expose a Docker daemon.

### How it works

The Slurm orchestrator connects to a Slurm submission host either over SSH or by
running Slurm commands locally:

* `transport=ssh` connects to a login node with the same SSH configuration used
  by the SSH integration.
* `transport=local` runs `sbatch`, `squeue`, `scontrol`, and `scancel` on the
  current machine. Use this when the ZenML client or orchestration process
  already runs on a Slurm login node.

For static pipelines, ZenML submits one Slurm job per step and wires the jobs
together with `afterok` dependencies. Slurm handles the dependency graph, and
ZenML reconciles job state through batched `squeue` lookups plus sentinel files
written by the job scripts.

For dynamic pipelines, ZenML submits a single orchestration job that runs
ZenML's dynamic runner inside the orchestrator image. Every step of the
pipeline executes inline within that job's allocation, so size the job with
pipeline-level resource settings. The orchestrator deliberately does not
submit per-step child jobs from the orchestration job: an active Slurm job
that queues and waits on new jobs deadlocks under per-user job limits and
blocks its own allocation while the children sit in the queue. If individual
steps need their own Slurm allocation, run them through the Slurm step
operator instead.

The orchestrator supports `CONTINUE_ON_FAILURE`, `STOP_ON_FAILURE`, and
`FAIL_FAST` execution modes. In continue-on-failure mode, independent sibling
jobs are left running when another branch fails. In stop-on-failure and
fail-fast modes, unfinished jobs are cancelled.

### How to use it

Install the Slurm integration:

```shell
zenml integration install slurm
```

Register the orchestrator for a remote login node:

```shell
zenml orchestrator register <ORCHESTRATOR_NAME> \
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

For a client that already runs on a Slurm login node, use local transport:

```shell
zenml orchestrator register <ORCHESTRATOR_NAME> \
    --flavor=slurm \
    --transport=local \
    --workdir=/shared/zenml-runs \
    --container_runtime=apptainer
```

Create or update a stack with the Slurm orchestrator, a remote artifact store, a
container registry, and an image builder:

```shell
zenml stack register <STACK_NAME> \
    -o <ORCHESTRATOR_NAME> \
    -a <REMOTE_ARTIFACT_STORE> \
    -c <CONTAINER_REGISTRY> \
    -i <IMAGE_BUILDER> \
    --set
```

You can now run a pipeline as usual:

```shell
python file_that_runs_a_zenml_pipeline.py
```

### Configuration options

Key registration-time options:

| Option | Description |
|--------|-------------|
| `transport` | `ssh` to connect to a remote login node, or `local` to run Slurm commands on the current machine. |
| `hostname`, `username`, `port` | SSH connection details. Required for `transport=ssh`. |
| `ssh_key_path` | Path to a private key on the submitting machine. Use for normal local submissions. |
| `ssh_private_key`, `ssh_key_passphrase` | Private key content and optional passphrase. Use ZenML secrets for these values. |
| `verify_host_key`, `known_hosts_path` | Host-key verification settings inherited from the SSH integration. Verification is enabled by default. |
| `workdir` | Shared directory used to stage per-run Slurm files. Must be visible from the submission host and compute nodes. |
| `container_runtime` | One of `apptainer`, `singularity`, `pyxis`, or `docker`. |
| `partition`, `time_limit`, `account`, `qos` | Common Slurm scheduling directives mapped to `#SBATCH` lines. |
| `extra_sbatch_directives` | Additional raw `#SBATCH` options such as `--constraint=a100`, `--reservation=<name>`, or `--exclusive`. |
| `container_mounts` | Host-path to container-path mounts, for example `{'/scratch/user': '/scratch'}`. |
| `container_run_args` | Additional arguments passed to the selected container runtime. |

You can override Slurm job settings per pipeline or per step:

```python
from zenml import step
from zenml.integrations.slurm.flavors.slurm_orchestrator_flavor import (
    SlurmOrchestratorSettings,
)

gpu_settings = SlurmOrchestratorSettings(
    partition="gpu",
    time_limit="2:00:00",
    account="ml-research",
    extra_sbatch_directives=["--constraint=a100"],
    container_mounts={"/scratch/$USER": "/scratch"},
)


@step(settings={"orchestrator": gpu_settings})
def train_model() -> None:
    ...
```

ZenML maps standard step resource settings to Slurm directives:

* `cpu_count` becomes `--cpus-per-task`.
* memory becomes `--mem`.
* `gpu_count` becomes `--gres=gpu:<count>`.

### Dynamic pipeline notes

Dynamic pipelines run entirely inside one long-running orchestration job. Keep
these operational details in mind:

* Size the orchestration job for the whole run: set resource settings at the
  pipeline level (CPU, memory, GPUs) — every step executes inside this one
  allocation.
* Configure `time_limit`, `partition`, `account`, `qos`, and any site-required
  `extra_sbatch_directives` so the orchestration job is allowed to run for the
  full duration of the pipeline, not just one step.
* The orchestration container must be able to reach the ZenML server and the
  artifact store. It never talks to the Slurm scheduler itself.

### Security and cleanup

ZenML stages each Slurm job in an owner-only run directory under `workdir`. The
environment file and any registry authentication files are written with `0600`
permissions and are not passed as command-line arguments. Job scripts install an
`EXIT` trap that records the exit code and removes credential-bearing files.

Static pipeline runs also submit an `afterany` cleanup job for staged sensitive
files. Cancellation paths explicitly scrub the known sensitive files when a
pending job is cancelled before its job script starts.

### Limitations

The current Slurm orchestrator is intentionally conservative:

* It runs one containerized Slurm job per ZenML step.
* It does not manage ZenML schedules. Trigger scheduled runs from cron, CI, or
  another scheduler.
* It does not provide first-class helpers for MPI, multi-node training, Slurm
  arrays, pre-staged SIF images, or `sacct`/accounting-based reconciliation.
* Advanced cluster requirements should be passed through
  `extra_sbatch_directives` and validated on a real cluster before relying on
  them in production.

Check out the [SDK docs](https://sdkdocs.zenml.io/latest/) for the full API
reference.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
