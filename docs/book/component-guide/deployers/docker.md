---
description: Deploying your pipelines locally with Docker.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Docker Deployer

The Docker deployer is a [deployer](./) flavor that comes built-in with ZenML and deploys your pipelines locally using Docker.

## When to use it

You should use the Docker deployer if:

* you need a quick and easy way to deploy your pipelines locally.
* you want to debug issues that happen when deploying your pipeline in Docker containers without waiting and paying for remote infrastructure.
* you need an easy way to test out how pipeline deployments work

## How to deploy it

To use the Docker deployer, you only need to have [Docker](https://www.docker.com/) installed and running.

## How to use it

To use the Docker deployer, you can register it and use it in your active stack:

```shell
zenml deployer register docker --flavor=docker

# Register and activate a stack with the new orchestrator
zenml stack register docker-deployer -D docker -o default -a default --set
```
{% hint style="info" %}
ZenML will build a local Docker image called `zenml:<PIPELINE_NAME>` and use it to deploy your pipeline as a Docker container. Check out [this page](https://docs.zenml.io/how-to/customize-docker-builds/) if you want to learn more about how ZenML builds these images and how you can customize them.
{% endhint %}

You can now deploy your ZenML pipeline using the Docker deployer:

```shell
zenml pipeline deploy my_module.my_pipeline
```

### Additional configuration

For additional configuration of the Local Docker orchestrator, you can pass the following `DockerDeployerSettings` attributes defined in the `zenml.deployers.docker.docker_deployer` module when configuring the deployer or defining or deploying your pipeline:

* Basic settings common to all Deployers:

  * `auth_key`: A user-defined authentication key to use to authenticate with deployment API calls.
  * `generate_auth_key`: Whether to generate and use a random authentication key instead of the user-defined one.
  * `lcm_timeout`: The maximum time in seconds to wait for the deployment lifecycle management to complete.

* Docker-specific settings:

  * `port`: The port to expose the deployment on.
  * `allocate_port_if_busy`: If True, allocate a free port if the configured port is busy.
  * `port_range`: The range of ports to search for a free port.
  * `run_args`: Arguments to pass to the `docker run` call. A full list of what can be passed in via the `run_args` can be found [in the Docker Python SDK documentation](https://docker-py.readthedocs.io/en/stable/containers.html).

Check out [this docs page](https://docs.zenml.io/concepts/steps_and_pipelines/configuration) for more information on how to specify settings.

For example, if you wanted to specify the port to use for the deployment, you would configure settings as follows:

```python
from zenml import step, pipeline
from zenml.deployers.docker.docker_deployer import DockerDeployerSettings


@step
def greet(name: str) -> str:
    return f"Hello {name}!"


settings = {
    "deployer": DockerDeployerSettings(
        run_args={"port": 8000}
    )
}

@pipeline(settings=settings)
def greet_pipeline(name: str = "John"):
    greet(name=name)
```
