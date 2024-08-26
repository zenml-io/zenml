---
description: Executing individual steps in Modal.
---

# Modal Step Operator

[Modal](https://modal.com) is a platform for running cloud infrastructure. It offers specialized compute instances to run your code and has a fast execution time, especially around building Docker images and provisioning hardware. ZenML's Modal step operator allows you to submit individual steps to be run on Modal compute instances.

### When to use it

You should use the Modal step operator if:

* You need fast execution time for steps that require computing resources (CPU, GPU, memory).
* You want to easily specify the exact hardware requirements (e.g., GPU type, CPU count, memory) for each step.
* You have access to Modal.

### How to deploy it

To use the Modal step operator:

* [Sign up for a Modal account](https://modal.com/signup) if you haven't already.
* Install the Modal CLI by running `pip install modal` and authenticate by running `modal setup` in your terminal.

### How to use it

To use the Modal step operator, we need:

* The ZenML `modal` integration installed. If you haven't done so, run

  ```shell
  zenml integration install modal
  ```
* Docker installed and running.
* A cloud artifact store as part of your stack. This is needed so that both your
  orchestration environment and Modal can read and write step artifacts. Any
  cloud artifact store supported by ZenML will work with Modal.
* A cloud container registry as part of your stack. Any cloud container
  registry supported by ZenML will work with Modal.

We can then register the step operator:

```shell
zenml step-operator register <NAME> --flavor=modal
zenml stack update -s <NAME> ...
```

Once you added the step operator to your active stack, you can use it to execute individual steps of your pipeline by specifying it in the `@step` decorator as follows:

```python
from zenml import step


@step(step_operator=<NAME>)
def trainer(...) -> ...:
    """Train a model."""
    # This step will be executed in Modal.
```

{% hint style="info" %}
ZenML will build a Docker image which includes your code and use it to run your steps in Modal. Check out [this page](../../how-to/customize-docker-builds/README.md) if you want to learn more about how ZenML builds these images and how you can customize them.
{% endhint %}

#### Additional configuration

You can specify the hardware requirements for each step using the
`ResourceSettings` class as described in our documentation on [resource settings](../../how-to/training-with-gpus/training-with-gpus.md):

```python
from zenml.config import ResourceSettings
from zenml.integrations.modal.flavors import ModalStepOperatorSettings

modal_settings = ModalStepOperatorSettings(gpu="A100")
resource_settings = ResourceSettings(
    cpu=2,
    memory="32GB"
)

@step(
    step_operator="modal", # or whatever name you used when registering the step operator
    settings={
        "step_operator.modal": modal_settings,
        "resources": resource_settings
    }
)
def my_modal_step():
    ...
```

This will run `my_modal_step` on a Modal instance with 1 A100 GPU, 2 CPUs, and
32GB of CPU memory.

Check out the [Modal docs](https://modal.com/docs/reference/modal.gpu) for the
full list of supported GPU types and the [SDK
docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-modal/#zenml.integrations.modal.flavors.modal\_step\_operator\_flavor.ModalStepOperatorSettings)
for more details on the available settings.
