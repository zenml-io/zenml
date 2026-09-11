---
description: Run selected Python steps as single-GPU Nebius Serverless Jobs.
---

# Nebius Serverless

The experimental `nebius` step operator runs a selected Python step as a
[Nebius Serverless Job](https://docs.nebius.com/serverless/jobs/manage).
ZenML builds the step image and uses its normal entrypoint and materializers to
preserve step identity, artifact lineage, and downstream input loading.

{% hint style="warning" %}
This integration currently supports static pipelines with the **local
orchestrator**, one regular GPU per Job, and **no automatic step retries**.
Live Nebius validation is pending. It does not provision Endpoints or use Token
Factory. Dynamic pipelines, command steps, preemptible instances, multi-node
execution, resource pools, and automatic recovery after orchestrator loss are
not supported.
{% endhint %}

## Prerequisites

You need a ZenML server reachable from both your launcher and the GPU Job,
a remote artifact store, an image builder, and a remote container registry.
A server on your laptop's loopback address is not reachable from a cloud Job.
Ensure your selected subnet can reach the server, storage, and registry.

The launcher needs Nebius permissions to create, get, list, and cancel Jobs in
one project. Use service-account credentials with token renewal. Keep their
credentials file only on the launcher; never include it in the build context.
The operator uses the standard Nebius SDK authentication chain when no
`credentials_file` is configured. When using native secret versions, that same
identity must also be allowed to read their payloads; permission to create or
inspect secret metadata is insufficient. Verify the credentials file belongs to
the intended service account rather than assuming it matches your CLI profile.

Install the optional integrations:

```shell
zenml integration install nebius s3
```

The initial SDK requirement is `nebius>=0.6.8,<0.7`. The S3 integration is needed
only if you use an S3 artifact store. Existing remote artifact stores may also
work if their dependencies and credentials are available inside the image.

## Configure the stack

Register a step operator with your project, subnet, and an explicit GPU preset:

```shell
zenml step-operator register nebius-gpu --flavor=nebius \
    --project_id="$NEBIUS_PROJECT_ID" \
    --subnet_id="$NEBIUS_SUBNET_ID" \
    --credentials_file=/secure/nebius-credentials.json \
    --platform=gpu-l40s-a \
    --preset=1gpu-8vcpu-32gb
```

Add it to a stack that already has your remote artifact store, registry and
image builder. For example, using the names of your existing components:

```shell
zenml stack register nebius-stack \
    -o default -a remote-artifacts -c remote-registry \
    -i image-builder -s nebius-gpu
zenml stack set nebius-stack
```

For Nebius Object Storage, reuse the [S3 artifact store](../artifact-stores/s3.md)
and set `client_kwargs.endpoint_url` to your regional storage endpoint. Configure
S3 credentials through ZenML secret references or the worker environment. A
local AWS profile is not automatically available in the Job. Mounting a bucket
as a filesystem does not configure a ZenML artifact store.

Private image pulls use the existing Nebius registry configuration or an
explicit `registry_secret_version` on the step operator. For the SDK field,
that secret version must contain `REGISTRY_USERNAME` and `REGISTRY_PASSWORD`.
Build-time push credentials remain configured on the ZenML container registry.
For Nebius Container Registry, use the registry path from its Docker commands
(the registry ID without the `registry-` prefix), followed by your image namespace
in `default_repository`. See the [registry quickstart](https://docs.nebius.com/container-registry/quickstart).
Check both paths independently before launching expensive workloads.

## Select the GPU step

```python
from zenml import pipeline, step
from zenml.integrations.nebius.flavors import NebiusStepOperatorSettings


@step
def prepare() -> list[list[float]]:
    return [[1.0, 2.0], [3.0, 4.0]]


@step(
    step_operator="nebius-gpu",
    settings={
        "step_operator": NebiusStepOperatorSettings(
            platform="gpu-l40s-a",
            preset="1gpu-8vcpu-32gb",
            timeout_seconds=3600,
        )
    },
)
def score_on_gpu(rows: list[list[float]]) -> list[float]:
    import torch

    tensor = torch.tensor(rows, device="cuda")
    return tensor.square().sum(dim=1).cpu().tolist()


@step
def summarize(scores: list[float]) -> None:
    print(scores)  # [5.0, 25.0]


@pipeline
def scoring_pipeline():
    summarize(score_on_gpu(prepare()))
```

Configure the step's Docker settings with a CUDA-compatible base image,
PyTorch, your source code, and any custom materializers. Build for
`linux/amd64` for the selected GPU platform. Keep ZenML's stack requirement
installation enabled and ensure the image contains this integration. The
operator requires an immutable `@sha256:` image reference from the ZenML build.
A mutable tag is rejected before submission.

Keep the complete image reference, including `@sha256:` and its 64-character
digest, within **128 characters**. Live API checks accepted lengths 127 and 128
but rejected 129 and 143 with a Compute-label validation error whose message
incorrectly reported a 64-character limit. Use a short container-registry
`default_repository`, such as `<registry-id-without-prefix>/zenml` for Nebius
Container Registry, and rebuild with `DockerSettings(prevent_build_reuse=True)`
if the reference is too long. The operator
rejects oversized references before creating a submission receipt or Job;
it does not truncate the reference or replace its digest with a mutable tag.

The [example](https://github.com/zenml-io/zenml/tree/develop/examples/nebius_step_operator)
shows Docker configuration and the complete pipeline. Runtime secrets are sent
to the Job separately from the image. The operator does not copy your launcher's
entire environment. Treat values passed through ZenML's runtime environment as
sensitive, even though they are ordinary Python strings.

## Settings

Component settings provide defaults; step settings override them.

| Setting | Default | Meaning |
|---|---|---|
| `platform`, `preset` | Required before submission | Explicit GPU platform and a `1gpu-...` preset; capacity is not inferred |
| `disk_size_gib` | 100 | Container disk for image layers and local staging |
| `shm_size_gib` | 16 | Shared memory size |
| `timeout_seconds` | 3600 | Provider timeout, within the documented 1–168 hour range |
| `provisioning_timeout_seconds` | 1800 | Launcher provisioning budget |
| `total_timeout_seconds` | 7200 | Launcher total supervision budget, including startup |
| `cancel_timeout_seconds` | 120 | Budget for cancellation confirmation |
| `request_timeout_seconds` | 30 | Budget for an individual SDK request and authorization |
| `poll_interval_seconds` | 5 | Poll interval |
| `publication_grace_seconds` | 30 | Grace period for ZenML result publication after provider completion |
| `public_ip` | `False` | Explicit public IP assignment; configure routing independently |
| `environment_secret_versions` | `{}` | Environment name → existing Nebius secret version ID |

The generic resource settings must be unset, or contain only `gpu_count=1`.
Conflicting CPU/memory/GPU-class requests and resource-pool settings fail instead
of being silently ignored. The provider validates whether the chosen
platform/preset pair exists and is available in your project.

Native environment secrets must use payload keys matching the variable names.
They cannot override variables already supplied by ZenML or names beginning
with `ZENML_`. For example, use a dedicated existing version for a model access
token. The integration does not create or delete secrets automatically.

Set supervision budgets for the workload, and allow startup time in addition to
training time. A request already in progress and ZenML metadata operations can
extend elapsed time beyond a polling deadline. Cancel acknowledgment is not
confirmation that compute has stopped.

## Outcomes, cancellation, and recovery

A successful Job is not sufficient on its own: the Python step must also
publish a successful ZenML result and its expected artifact records. Missing
publication, materializer failure, or a container that exits zero without
running the entrypoint cannot become an implicit successful step. ZenML cache
hits bypass submission normally.

The `nebius_submission` run metadata contains a non-secret receipt: submission
UUID/idempotency key, project, step/run/component identity, image digest, spec
fingerprint, timestamps, operation ID, Job ID, and cleanup status. Failed SDK
submissions also retain the gRPC status name and a valid request UUID, without
raw provider error messages. Inspect the
receipt on the step run. The Job ID also appears in the launcher's log:

```shell
nebius ai job logs <job-id> --follow
```

Ctrl-C while the local launcher waits attempts cancellation of the acknowledged
Job ID and preserves the original interruption. You can also cancel explicitly
from a client connected to the same server and stack:

```python
from zenml.client import Client

client = Client()
step_run = client.get_run_step("<step-run-id>")
operator = client.active_stack.step_operator
operator.cancel(step_run)
```

Use the matching named operator if your stack has several. The waiter also
observes ZenML cancellation status. Support for every dashboard/orchestrator
stop path is not implied. SIGKILL, loss of the host, or loss of connectivity can
prevent local cancellation and cleanup hooks from running.

Create and Cancel mutations have SDK retries disabled. If Create fails after
possibly reaching the provider, **do not resubmit**. The receipt remains available
even when no Job ID was returned. Names are not unique; a lookup by name is
insufficient. Inspect all candidate Jobs before deciding what to do:

```python
candidates = operator.find_submission_jobs(step_run)
print(candidates)
```

This bounded read-only search paginates all project Jobs and matches identity
labels, image and subnet. It does not attach, cancel or resubmit anything. No
matches can mean delayed visibility, not absence. Multiple matches require
manual investigation. If there is an operation ID, inspect that operation too.
Once the actual Job is identified, use its ID in the Nebius CLI/console. Only
start a fresh pipeline run after you have reconciled the earlier workload.

One active submitter per step run is required. The receipt is not a distributed
lock; automatic ZenML retries are rejected. A repeated call to `submit` for a
step that already has a receipt does not create another Job. Read polling can
retry transient failures within the saved deadline, but it never replays Create.

## Cleanup limits

The operator retains Job records and never deletes shared artifact storage,
registry images or user volumes. Cleanup metadata distinguishes:

- `NOT_CONFIRMED`: no terminal workload observation yet.
- `WORKLOAD_TERMINAL`: a terminal Job state was observed; this does **not** verify
  deletion of the underlying VM and boot disk.
- `UNCONFIRMED`: cancellation could not be confirmed within the budget.

Nebius documents automatic VM/boot-disk cleanup. Independently verify those
resources during live acceptance tests, especially on provider timeout. A
terminal Job record is not evidence that every resource was removed. See
[Nebius lifecycle documentation](https://docs.nebius.com/serverless/lifecycle).
The integration does not compensate for provider cleanup issues by blindly
issuing Compute disk deletion requests.

For unattended runs requiring orphan cleanup after launcher loss, operate an
independent watchdog with persisted receipts and inspect/cancel permissions.
Neither the provider timeout nor the local cleanup hook proves a universal
orphan-resource bound. Live GPU execution, credentials, private pulls and
underlying resource cleanup must be validated in your environment before
production use.
