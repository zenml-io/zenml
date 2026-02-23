---
description: Executing individual steps as Hugging Face Jobs.
---

# Hugging Face Jobs Step Operator

[Hugging Face Jobs](https://huggingface.co/docs/hub/jobs) lets you run Docker containers on Hugging Face infrastructure with access to a range of CPU and GPU hardware. ZenML's Hugging Face Jobs step operator submits individual pipeline steps as HF Jobs, polls until completion, and streams logs back to ZenML.

### When to use it

You should use the Hugging Face Jobs step operator if:

* You want to run individual steps on Hugging Face infrastructure with GPU or specialized CPU resources.
* You already use the Hugging Face ecosystem (models, datasets, Spaces) and want to keep your compute there too.
* You have a Hugging Face Pro, Team, or Enterprise account with Jobs access.

### How to deploy it

To use the Hugging Face Jobs step operator you need:

* A [Hugging Face account](https://huggingface.co/join) with Jobs access (Pro, Team, or Enterprise plan).
* A Hugging Face API token with appropriate permissions. You can create one at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).
* `huggingface_hub >= 0.30.0` (the Jobs API was introduced in this version). The ZenML integration install handles this, but if you see an error about the Jobs API not being available, upgrade with:

```shell
pip install 'huggingface_hub>=0.30.0'
```

### How to use it

To use the Hugging Face Jobs step operator, we need:

* The ZenML `huggingface` integration installed. If you haven't done so, run:

```shell
zenml integration install huggingface
```

* A remote artifact store as part of your stack (e.g., S3, GCS, Azure Blob). The Job cannot access local files.
* A remote container registry as part of your stack. The Job pulls the Docker image from this registry.
* An image builder as part of your stack (e.g., local Docker builder).

We can then register the step operator and add it to our stack:

```shell
# Option 1: Pass token directly (less secure)
zenml step-operator register <NAME> \
    --flavor=huggingface-jobs \
    --token=<YOUR_HF_TOKEN>

# Option 2: Reference a ZenML secret (recommended)
zenml secret create hf_secret --token=<YOUR_HF_TOKEN>
zenml step-operator register <NAME> \
    --flavor=huggingface-jobs \
    --token='{{hf_secret.token}}'
```

You can also set component-level defaults during registration:

```shell
zenml step-operator register <NAME> \
    --flavor=huggingface-jobs \
    --token='{{hf_secret.token}}' \
    --hardware_flavor=cpu-basic \
    --timeout=30m \
    --namespace=my-org
```

Add the step operator to your stack:

```shell
zenml stack update -s <NAME> ...
```

Once the step operator is part of your active stack, use it in individual steps:

```python
from zenml import step


@step(step_operator=True)
def trainer(...) -> ...:
    """Train a model on Hugging Face Jobs."""
    # This step will be executed as a HF Job.
```

{% hint style="info" %}
ZenML builds a Docker image that includes your code and uses it to run your step as a Hugging Face Job. Check out [this page](https://docs.zenml.io/how-to/customize-docker-builds) if you want to learn more about how ZenML builds these images and how you can customize them.
{% endhint %}

#### Token resolution

The operator resolves the HF token using this priority chain:

1. **Component config** — the `token` field on the step operator registration (supports `{{secret.key}}` references).
2. **Environment variable** — `HF_TOKEN` or `HUGGING_FACE_HUB_TOKEN`.
3. **Cached login** — token saved by `huggingface-cli login`.

If none of these are available, the step will fail with a clear error message.

#### Environment variables and secrets

By default (`pass_env_as_secrets=True`), all ZenML-provided environment variables — which may include cloud credentials for your artifact store — are sent as **HF encrypted secrets**. These are encrypted server-side and are not visible in job specs.

Set `pass_env_as_secrets=False` if you prefer to send them as plain environment variables instead. Regardless of this setting, the HF token is always injected as an encrypted secret into the job.

#### Additional configuration

You can override hardware, timeout, and namespace on a per-step basis using `HuggingFaceJobsStepOperatorSettings`:

```python
from zenml import step
from zenml.integrations.huggingface.flavors import (
    HuggingFaceJobsStepOperatorSettings,
)

hf_settings = HuggingFaceJobsStepOperatorSettings(
    hardware_flavor="a10g-small",
    timeout="2h",
    namespace="my-org",
)


@step(
    step_operator=True,
    settings={"step_operator": hf_settings},
)
def gpu_trainer(...) -> ...:
    """Train on GPU via Hugging Face Jobs."""
    ...
```

**Component-level configuration** (`HuggingFaceJobsStepOperatorConfig`):

| Field                   | Type             | Default | Description                                              |
| ----------------------- | ---------------- | ------- | -------------------------------------------------------- |
| `token`                 | `Optional[str]`  | `None`  | HF API token (supports `{{secret.key}}` references)      |
| `hardware_flavor`       | `Optional[str]`  | `None`  | Default hardware flavor for all steps                    |
| `timeout`               | `Optional`       | `None`  | Default job timeout (seconds or string like `30m`, `2h`) |
| `namespace`             | `Optional[str]`  | `None`  | HF namespace (user or organization)                      |
| `pass_env_as_secrets`   | `bool`           | `True`  | Route env vars through HF encrypted secrets              |
| `stream_logs`           | `bool`           | `True`  | Stream job logs during execution                         |
| `poll_interval_seconds` | `float`          | `10.0`  | Seconds between job status polls                         |

**Per-step overrides** (`HuggingFaceJobsStepOperatorSettings`):

| Field              | Type            | Default | Description                                               |
| ------------------ | --------------- | ------- | --------------------------------------------------------- |
| `hardware_flavor`  | `Optional[str]` | `None`  | e.g. `cpu-basic`, `a10g-small`, `a100-large`              |
| `timeout`          | `Optional`      | `None`  | Job timeout (seconds or duration string like `30m`, `2h`) |
| `namespace`        | `Optional[str]` | `None`  | HF namespace for this job                                 |

{% hint style="info" %}
Per-step settings override component-level defaults. Run `hf jobs hardware` (from the `huggingface_hub` CLI) to see the full list of available hardware flavors.
{% endhint %}

Check out the [SDK docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-huggingface/) for the full API reference.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
