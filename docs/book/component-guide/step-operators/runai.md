---
description: Executing individual steps on Run:AI clusters with fractional GPU support.
---

# Run:AI Step Operator

ZenML's Run:AI step operator allows you to submit individual steps to be run on [Run:AI](https://www.nvidia.com/en-us/software/run-ai/) clusters as training workloads with support for fractional GPU allocation.

### When to use it

You should use the Run:AI step operator if:

* one or more steps of your pipeline require GPU resources that are not provided by your orchestrator.
* you need fractional GPU allocation (e.g., 0.5 GPU per step) to maximize resource utilization.
* you're already using Run:AI for workload management.
* you want to leverage Run:AI's scheduling and resource management features.

### Key Features

* **Fractional GPU Support**: Allocate portions of a GPU (e.g., 0.25, 0.5, 0.75) to maximize resource utilization
* **Training Workloads**: Submit individual ZenML steps as Run:AI training workloads
* **Dynamic Pipeline Support**: Supports asynchronous step submission and monitoring in dynamic pipelines
* **Project-based Resource Management**: Workloads are organized by Run:AI projects with quota policies
* **SaaS and Self-hosted**: Works with both Run:AI SaaS and self-hosted deployments

![Run:AI interface](../../.gitbook/assets/runai-interface.png)

### How to deploy it

The Run:AI step operator requires access to a Run:AI cluster. You will need:

* Access to a Run:AI cluster (SaaS or self-hosted)
* A Run:AI project with sufficient resource quota
* Run:AI API credentials (client ID and secret):
  * Navigate to Run:AI control plane → Access → Service accounts (called "Settings → Applications" on older versions)
  * Create a new [service account to obtain client credentials](https://run-ai-docs.nvidia.com/self-hosted/infrastructure-setup/authentication/service-accounts)
  * Assign it an access rule with an appropriate role and scope (see [Run:AI service account permissions](#runai-service-account-permissions) below)

### Run:AI service account permissions

The `client_id` and `client_secret` you pass to the step operator authenticate as a Run:AI **service account** (formerly called "Application"). Run:AI uses RBAC of the form `<subject> is a <role> in a <scope>`, so giving the service account the right permissions means picking a role and a scope.

The ZenML integration only ever exercises a small set of Run:AI API operations under the hood, so it does not need a broad role. The full surface area is:

| Operation | Run:AI entity → action |
|---|---|
| Resolve project by name | Projects → View |
| Resolve cluster | Clusters (or Clusters minimal) → View |
| Submit training workload | Trainings → Create |
| Poll workload status | Trainings → View |
| Suspend on cancel/timeout | Trainings → Edit |
| Delete workload (only if `delete_on_failure=True`) | Trainings → Delete |

That's it. The integration constructs the full workload spec from your `RunAIStepOperatorSettings` and submits it directly, so it does **not** need access to Workspaces, Inferences, Environments, Compute resources, Credentials, Data sources, Templates, Policies, Users, Access rules, or Roles.

#### Recommended role by Run:AI version

**Run:AI self-hosted v2.24+ — use `AI practitioner` at project scope.** Run:AI 2.24 deprecated the legacy researcher/engineer roles in favor of `AI practitioner`, `Data and storage administrator`, and `Project administrator`. `AI practitioner` carries View/Edit/Create/Delete on Trainings and Workloads, View on Projects, and View on Clusters minimal and Node pools minimal — exactly matching what the integration needs. It is the smallest predefined role in 2.24 that fully covers the integration.

**Run:AI v2.23 and earlier (including older self-hosted clusters and SaaS tenants not yet on 2.24) — use `L1 researcher` at project scope.** `L1 researcher` has VECD on Trainings, Workloads, and Workspaces, plus View on Projects, Clusters, and Node pools — also a complete superset of what's needed. Avoid `L2 researcher` (no dashboard view, no real security gain over L1 for an automated submitter) and avoid `ML engineer` (has VECD on Inferences, not Trainings — the wrong direction for ZenML training-style workloads).

**Tightest least-privilege option (v2.24+) — build a custom role via the Roles API.** From v2.24 onward, administrators can compose custom roles from permission sets using `POST /api/v2/authorization/roles`. For the ZenML step operator the minimal custom role is:

* Trainings — View, Create, Edit (add Delete only if you intend to set `delete_on_failure=True`)
* Workloads — View (the status path returns the generic workload object too)
* Projects — View
* Clusters minimal — View
* Node pools minimal — View (only needed if you pass `node_pools` in step settings)

#### Scope: always use the Project scope

Run:AI scopes are Projects, Departments, Clusters, or Account. Always assign the role at the specific **Project** scope that matches the `project_name` in your `RunAIStepOperatorConfig`. Assigning the role at Department, Cluster, or Account scope would let the same client ID submit workloads into projects ZenML was never configured to use, which defeats the point of a per-stack service account. The "Clusters minimal" / "Node pools minimal" permission sets exist so a project-scoped role can still resolve cluster and node-pool identifiers without leaking full cluster visibility.

#### Quick setup

1. In the Run:AI control plane, go to **Access → Service accounts → + NEW SERVICE ACCOUNT**, name it (e.g., `zenml-step-operator`), and copy the client ID and client secret. The secret is only displayed once at creation time.
2. In **Access → Access rules → + ACCESS RULE**, set the subject to that service account, the role to `AI practitioner` (v2.24+) or `L1 researcher` (older), and the scope to the specific Run:AI project ZenML will submit into.
3. Confirm the project has sufficient GPU/CPU/memory quota on the relevant node pool — the workload will sit in `Pending` indefinitely (and eventually trip `pending_timeout`) if it doesn't.
4. If you use a private container registry, create a Docker-registry credential in the Run:AI project and pass its name as `image_pull_secret_name` when registering the step operator.

### How to use it

To use the Run:AI step operator, we need:

* The ZenML `runai` integration installed. If you haven't done so, run:

    ```shell
    zenml integration install runai
    ```

* A [remote artifact store](https://docs.zenml.io/stacks/artifact-stores/) as part of your stack. This is needed so that both your orchestration environment and Run:AI workloads can read and write step artifacts.

* A [remote container registry](https://docs.zenml.io/stacks/container-registries/) to store the Docker images that will be used to run your steps.

* An [image builder](https://docs.zenml.io/stacks/image-builders/) to build the Docker images.

We can then register the step operator, using [ZenML secrets](https://docs.zenml.io/concepts/secrets#python-sdk-3) to store the Run:AI client ID and secret:

```shell
zenml step-operator register <NAME> \
    --flavor=runai \
    --client_id={{runai_secret.client_id}} \
    --client_secret={{runai_secret.client_secret}} \
    --runai_base_url=<YOUR_RUNAI_URL> \
    --project_name=<YOUR_PROJECT_NAME>
```

We can then add the step operator to our active stack:

```shell
zenml stack update -s <NAME>
```

Once you added the step operator to your active stack, you can use it to execute individual steps of your pipeline by specifying it in the `@step` decorator:

```python
from zenml import step


@step(step_operator="<NAME>")
def trainer(...) -> ...:
    """Train a model on Run:AI."""
    # This step will be executed on Run:AI
```

{% hint style="info" %}
ZenML will build a Docker image which includes your code and use it to run your steps on Run:AI. Check out [this page](https://docs.zenml.io/how-to/customize-docker-builds/) if you want to learn more about how ZenML builds these images and how you can customize them.
{% endhint %}

The Run:AI step operator uses asynchronous workload submission under the hood. ZenML stores the Run:AI workload metadata for each step run and uses it for status monitoring and cancellation.

### Configuring GPU resources

You can configure GPU allocation using step operator settings:

```python
from zenml import step
from zenml.integrations.runai.flavors import RunAIStepOperatorSettings

# Request half a GPU
runai_settings = RunAIStepOperatorSettings(
    gpu_devices_request=1,
    gpu_portion_request=0.5,  # 0.5 = half GPU
    gpu_request_type="portion",
    cpu_core_request=2.0,
    cpu_memory_request="4G",
)

@step(
    step_operator="runai",
    settings={"step_operator": runai_settings}
)
def train_model():
    # This step runs with half a GPU
    ...
```

#### CPU-only workload

```python
settings = RunAIStepOperatorSettings(
    gpu_devices_request=0,  # No GPU
    cpu_core_request=8.0,
    cpu_memory_request="32G",
)
```

### Configuration options

#### Step Operator Configuration (set during registration)

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `client_id` | str | Yes | Run:AI client ID for API authentication |
| `client_secret` | str | Yes | Run:AI client secret for API authentication |
| `runai_base_url` | str | Yes | Run:AI control plane URL (e.g., `https://org.run.ai`) |
| `project_name` | str | Yes | Run:AI project name for workload submission |
| `cluster_name` | str | No | Run:AI cluster name (uses project's cluster if not specified) |
| `image_pull_secret_name` | str | No | Name of Run:AI image pull secret for private registries |
| `monitoring_interval` | float | No | Interval in seconds to poll workload status (default: 30) |
| `workload_timeout` | int | No | Maximum time in seconds for workload completion |
| `delete_on_failure` | bool | No | Delete failed workloads (default: False). Set to True to clean up failed runs |

#### Step Settings (per-step configuration)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `gpu_devices_request` | int | 1 | Number of GPUs to request |
| `gpu_portion_request` | float | 1.0 | Fractional GPU allocation (0.0-1.0) |
| `gpu_request_type` | str | "portion" | GPU allocation method: "portion" or "memory" |
| `gpu_memory_request` | str | None | GPU memory to request (e.g., "20Gi") when using memory type |
| `cpu_core_request` | float | 1.0 | Number of CPU cores to request |
| `cpu_memory_request` | str | "4G" | Memory to request (e.g., "4G", "8Gi") |
| `node_pools` | list | None | Ordered list of node pool names for scheduling |
| `node_type` | str | None | Node type label for GPU selection |
| `preemptibility` | str | None | "preemptible" or "non-preemptible" |
| `priority_class` | str | None | Kubernetes PriorityClass name |
| `large_shm_request` | bool | False | Request large /dev/shm for PyTorch DataLoader |

Environment variables are configured through the standard ZenML `environment` settings on steps or pipelines; the Run:AI step operator does not introduce an additional environment-specific setting.

### Troubleshooting

#### Common Issues

**Issue: "Project not found in Run:AI"**
- Ensure the project name exactly matches your Run:AI project
- Verify the service account has at least View permission on Projects within the project's scope

**Issue: "Failed to submit Run:AI workload" / 403 errors**
- Check that your client ID and secret are correct
- Verify your Run:AI base URL is accessible
- Verify the service account has View/Edit/Create/Delete permissions (or at minimum View+Create+Edit) on Trainings within the project scope — see [Run:AI service account permissions](#runai-service-account-permissions)
- Ensure your project has sufficient resource quota

**Issue: Workload stays in `Pending` and eventually times out**
- The Run:AI project most likely doesn't have enough quota on the requested node pool. Increase quota or pick a node pool with capacity via `node_pools`/`node_type` settings

**Issue: "runapy package not found"**
- Install the Run:AI integration: `zenml integration install runai`

#### Viewing Logs

Run:AI workload logs can be viewed in the Run:AI control plane UI:
1. Navigate to your Run:AI control plane
2. Go to Workloads → Training
3. Find your step workload and click to view logs

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
