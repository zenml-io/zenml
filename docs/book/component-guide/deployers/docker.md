---
description: Deploying your pipelines locally with Docker.
---

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

To use the Docker deployer, register it and then select it at deploy time:

```shell
zenml deployer register docker --flavor=docker
```
{% hint style="info" %}
ZenML will build a local Docker image called `zenml:<PIPELINE_NAME>` and use it to deploy your pipeline as a Docker container. Check out [this page](https://docs.zenml.io/how-to/customize-docker-builds/) if you want to learn more about how ZenML builds these images and how you can customize them.
{% endhint %}

You can now [deploy any ZenML pipeline](https://docs.zenml.io/concepts/deployment) using the Docker deployer by selecting it with the `-D`/`--deployer` option:

```shell
zenml pipeline deploy -D docker my_module.my_pipeline
```

{% hint style="warning" %}
**Local artifact stores are not supported with the Docker deployer.** By default, ZenML uploads your pipeline code to the artifact store and the deployment container downloads it on startup. A Docker container cannot reach a local artifact store, so the download fails and the container cannot import your pipeline (you will see a `ModuleNotFoundError` for your pipeline module). Use one of the following instead:

* a [remote artifact store](https://docs.zenml.io/stacks/artifact-stores/) or a [code repository](https://docs.zenml.io/user-guides/production-guide/connect-code-repository) that the container can access, or
* include the code in the image so nothing needs to be downloaded at runtime:

```python
from zenml.config import DockerSettings

docker_settings = DockerSettings(
    allow_including_files_in_images=True,
    allow_download_from_artifact_store=False,
    allow_download_from_code_repository=False,
)
```
{% endhint %}

### Additional configuration

For additional configuration of the Docker deployer, you can pass the following `DockerDeployerSettings` attributes defined in the `zenml.deployers.docker.docker_deployer` module when configuring the deployer or defining or deploying your pipeline:

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
        port=8000
    )
}

@pipeline(settings=settings)
def greet_pipeline(name: str = "John"):
    greet(name=name)
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
