---
description: Executing individual steps on Run:AI clusters with fractional GPU support.
---

# Run:AI Step Operator

ZenML's Run:AI step operator allows you to submit individual steps to be run on [Run:AI](https://www.run.ai/) clusters as training workloads with support for fractional GPU allocation.

### When to use it

You should use the Run:AI step operator if:

* one or more steps of your pipeline require GPU resources that are not provided by your orchestrator.
* you need fractional GPU allocation (e.g., 0.5 GPU per step) to maximize resource utilization.
* you're already using Run:AI for workload management.
* you want to leverage Run:AI's scheduling and resource management features.

### Key Features

* **Fractional GPU Support**: Allocate portions of a GPU (e.g., 0.25, 0.5, 0.75) to maximize resource utilization
* **Training Workloads**: Submit individual ZenML steps as Run:AI training workloads
* **Project-based Resource Management**: Workloads are organized by Run:AI projects with quota policies
* **SaaS and Self-hosted**: Works with both Run:AI SaaS and self-hosted deployments

![Run:AI interface](../../assets/runai-interface.png)

### How to deploy it

The Run:AI step operator requires access to a Run:AI cluster. You will need:

* Access to a Run:AI cluster (SaaS or self-hosted)
* A Run:AI project with sufficient resource quota
* Run:AI API credentials (client ID and secret):
  * Navigate to Run:AI control plane → Settings → Applications
  * Create a new [application to obtain client credentials](https://run-ai-docs.nvidia.com/saas/infrastructure-setup/authentication/service-accounts)

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
- Verify you have access to the project with your credentials

**Issue: "Failed to submit Run:AI workload"**
- Check that your client ID and secret are correct
- Verify your Run:AI base URL is accessible
- Ensure your project has sufficient resource quota

**Issue: "runapy package not found"**
- Install the Run:AI integration: `zenml integration install runai`

#### Viewing Logs

Run:AI workload logs can be viewed in the Run:AI control plane UI:
1. Navigate to your Run:AI control plane
2. Go to Workloads → Training
3. Find your step workload and click to view logs
