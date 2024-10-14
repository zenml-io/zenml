---
description: Using Docker images to run your pipeline.
---

# Specify Docker settings for a pipeline

When a [pipeline is run with a remote orchestrator](../configure-python-environments/README.md) a [Dockerfile](https://docs.docker.com/engine/reference/builder/) is dynamically generated at runtime. It is then used to build the Docker image using the [image builder](../configure-python-environments/README.md#image-builder-environment) component of your stack. The Dockerfile consists of the following steps:

* **Starts from a parent image** that has **ZenML installed**. By default, this will use the [official ZenML image](https://hub.docker.com/r/zenmldocker/zenml/) for the Python and ZenML version that you're using in the active Python environment. If you want to use a different image as the base for the following steps, check out [this guide](./docker-settings-on-a-pipeline.md#using-a-custom-parent-image).
* **Installs additional pip dependencies**. ZenML will automatically detect which integrations are used in your stack and install the required dependencies. If your pipeline needs any additional requirements, check out our [guide on including custom dependencies](specify-pip-dependencies-and-apt-packages.md).
* **Optionally copies your source files**. Your source files need to be available inside the Docker container so ZenML can execute your step code. Check out [this section](./which-files-are-built-into-the-image.md) for more information on how you can customize how ZenML handles your source files in Docker images.
* **Sets user-defined environment variables.**

The process described above is automated by ZenML and covers the most basic use cases. This section covers various ways to customize the Docker build process to fit your needs.

For a full list of configuration options, check out [the DockerSettings object on the SDKDocs](https://sdkdocs.zenml.io/latest/core_code_docs/core-config/#zenml.config.docker_settings.DockerSettings).

## How to configure settings for a pipeline

Customizing the Docker builds for your pipelines and steps is done using the [DockerSettings](https://sdkdocs.zenml.io/latest/core_code_docs/core-config/#zenml.config.docker_settings.DockerSettings) class which you can import like this:

```python
from zenml.config import DockerSettings
```

There are many ways in which you can supply these settings:

* Configuring them on a pipeline applies the settings to all steps of that pipeline:

```python
from zenml.config import DockerSettings
docker_settings = DockerSettings()

# Either add it to the decorator
@pipeline(settings={"docker": docker_settings})
def my_pipeline() -> None:
    my_step()

# Or configure the pipelines options
my_pipeline = my_pipeline.with_options(
    settings={"docker": docker_settings}
)
```

* Configuring them on a step gives you more fine-grained control and enables you to build separate specialized Docker images for different steps of your pipelines:

```python
docker_settings = DockerSettings()

# Either add it to the decorator
@step(settings={"docker": docker_settings})
def my_step() -> None:
    pass

# Or configure the step options
my_step = my_step.with_options(
    settings={"docker": docker_settings}
)
```

* Using a YAML configuration file as described [here](../use-configuration-files/README.md):

```yaml
settings:
    docker:
        ...

steps:
  step_name:
    settings:
        docker:
            ...
```

Check out [this page](../use-configuration-files/configuration-hierarchy.md) for more information on the hierarchy and precedence of the various ways in which you can supply the settings.

### Specifying Docker build options

If you want to specify build options that get passed to the build method of the [image builder](../configure-python-environments/README.md#image-builder-environment). For the default local image builder, these options get passed to the [`docker build` command](https://docker-py.readthedocs.io/en/stable/images.html#docker.models.images.ImageCollection.build).

```python
docker_settings = DockerSettings(build_config={"build_options": {...}})

@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

{% hint style="info" %}
If you're running your pipelines on MacOS with ARM architecture, the local Docker caching does not work unless you specify the target platform of the image:
```python
docker_settings = DockerSettings(build_config={"build_options": {"platform": "linux/amd64"}})

@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```
{% endhint %}

### Using a custom parent image

By default, ZenML performs all the steps described above on top of the [official ZenML image](https://hub.docker.com/r/zenmldocker/zenml/) for the Python and ZenML version in the active Python environment. To have more control over the entire environment used to execute your pipelines, you can either specify a custom pre-built parent image or a Dockerfile that ZenML uses to build a parent image for you.

{% hint style="info" %}
If you're going to use a custom parent image (either pre-built or by specifying a Dockerfile), you need to make sure that it has Python, pip, and ZenML installed for it to work. If you need a starting point, you can take a look at the Dockerfile that ZenML uses [here](https://github.com/zenml-io/zenml/blob/main/docker/base.Dockerfile).
{% endhint %}

#### Using a pre-built parent image

To use a static parent image (e.g., with internal dependencies installed) that doesn't need to be rebuilt on every pipeline run, specify it in the Docker settings for your pipeline:

```python
docker_settings = DockerSettings(parent_image="my_registry.io/image_name:tag")


@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

To use this image directly to run your steps without including any code or installing any requirements on top of it, skip the Docker builds by specifying it in the Docker settings:

```python
docker_settings = DockerSettings(
    parent_image="my_registry.io/image_name:tag",
    skip_build=True
)


@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

{% hint style="warning" %}
This is an advanced feature and may cause unintended behavior when running your pipelines. If you use this, ensure your code files are correctly included in the image you specified. Read in detail about this feature [here](./use-a-prebuilt-image.md) before proceeding.
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
