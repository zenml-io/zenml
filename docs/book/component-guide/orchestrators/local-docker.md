---
description: Orchestrating your pipelines to run in Docker.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Local Docker Orchestrator

The local Docker orchestrator is an [orchestrator](./orchestrators.md) flavor that comes built-in with ZenML and runs your pipelines locally using Docker.

### When to use it

You should use the local Docker orchestrator if:

* you want the steps of your pipeline to run locally in isolated environments.
* you want to debug issues that happen when running your pipeline in Docker containers without waiting and paying for remote infrastructure.

### How to deploy it

To use the local Docker orchestrator, you only need to have [Docker](https://www.docker.com/) installed and running.

### How to use it

To use the local Docker orchestrator, we can register it and use it in our active stack:

```shell
zenml orchestrator register <ORCHESTRATOR_NAME> --flavor=local_docker

# Register and activate a stack with the new orchestrator
zenml stack register <STACK_NAME> -o <ORCHESTRATOR_NAME> ... --set
```

You can now run any ZenML pipeline using the local Docker orchestrator:

```shell
python file_that_runs_a_zenml_pipeline.py
```

#### Additional configuration

For additional configuration of the Local Docker orchestrator, you can pass `LocalDockerOrchestratorSettings` when defining or running your pipeline. Check out the [SDK docs](https://sdkdocs.zenml.io/latest/core\_code\_docs/core-orchestrators/#zenml.orchestrators.local\_docker.local\_docker\_orchestrator.LocalDockerOrchestratorSettings) for a full list of available attributes and [this docs page](../../how-to/use-configuration-files/runtime-configuration.md) for more information on how to specify settings. A full list of what can be passed in via the `run_args` can be found [in the Docker Python SDK documentation](https://docker-py.readthedocs.io/en/stable/containers.html).

For more information and a full list of configurable attributes of the local Docker orchestrator, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/core\_code\_docs/core-orchestrators/#zenml.orchestrators.local\_docker.local\_docker\_orchestrator.LocalDockerOrchestrator) .

For example, if you wanted to specify the CPU count available for the Docker image (note: only configurable for Windows), you could write a simple pipeline like the following:

```python
from zenml import step, pipeline
from zenml.orchestrators.local_docker.local_docker_orchestrator import (
    LocalDockerOrchestratorSettings,
)


@step
def return_one() -> int:
    return 1


settings = {
    "orchestrator.local_docker": LocalDockerOrchestratorSettings(
        run_args={"cpu_count": 3}
    )
}


@pipeline(settings=settings)
def simple_pipeline():
    return_one()
```

#### Enabling CUDA for GPU-backed hardware

Note that if you wish to use this orchestrator to run steps on a GPU, you will need to follow [the instructions on this page](../../how-to/training-with-gpus/training-with-gpus.md) to ensure that it works. It requires adding some extra settings customization and is essential to enable CUDA for the GPU to give its full acceleration.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
