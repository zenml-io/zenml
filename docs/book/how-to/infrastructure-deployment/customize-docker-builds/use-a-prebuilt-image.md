---
description: "Skip building an image for your ZenML pipeline altogether."
---

# Use a prebuilt image for pipeline execution

When running a pipeline on a remote Stack, ZenML builds a Docker image with a base ZenML image and adds all of your project dependencies to it. Optionally, if a code repository is not registered and `allow_download_from_artifact_store` is not set to `True` in your `DockerSettings`, ZenML will also add your pipeline code to the image. This process might take significant time depending on how big your dependencies are, how powerful your local system is and how fast your internet connection is. This is because Docker must pull base layers and push the final image to your container registry. Although this process only happens once and is skipped if ZenML detects no change in your environment, it might still be a bottleneck slowing down your pipeline execution.

To save time and costs, you can choose to not build a Docker image every time your pipeline runs. This guide shows you how to do it using a prebuilt image, what you should include in your image for the pipeline to run successfully and other tips.

{% hint style="info" %}
Note that using this feature means that you won't be able to leverage any updates you make to your code or dependencies, outside of what your image already contains.
{% endhint %}

## How do you use this feature

The [`DockerSettings`](./docker-settings-on-a-pipeline.md#specify-docker-settings-for-a-pipeline) class in ZenML allows you to set a parent image to be used in your pipeline runs and gives the ability to skip building an image on top of it.

To do this, just set the `parent_image` attribute of the `DockerSettings` class to the image you want to use and set `skip_build` to `True`.

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
You should make sure that this image is pushed to a registry from which the orchestrator/step operator/other components that require the image can pull, without any involvement by ZenML.
{% endhint %}

## What the parent image should contain

When you run a pipeline with a pre-built image, skipping the build process, ZenML will not build any image on top of it. This means that the image you provide to the `parent_image` attribute of the `DockerSettings` class has to contain all the dependencies that are needed to run your pipeline, and optionally any code files if you don't have a code repository registered, and the `allow_download_from_artifact_store` flag is set to `False`.

{% hint style="info" %}
Note that this is different from the case where you [only specify a parent image](./docker-settings-on-a-pipeline.md#using-a-pre-built-parent-image) and don't want to `skip_build`. In the latter, ZenML still builds the image but does it on top of your parent image and not the base ZenML image.
{% endhint %}
{% hint style="info" %}
If you're using an image that was already built by ZenML in a previous pipeline run, you don't need to worry about what goes in it as long as it was built for the **same stack** as your current pipeline run. You can use it directly.
{% endhint %}

The following points are derived from how ZenML builds an image internally and will help you make your own images.

### Your stack requirements

A ZenML Stack can have different components and each comes with its own requirements. You need to ensure that your image contains them. The following is how you can get a list of stack requirements.

```python
from zenml.client import Client

stack_name = <YOUR_STACK>
# set your stack as active if it isn't already
Client().set_active_stack(stack_name)

# get the requirements for the active stack
active_stack = Client().active_stack
stack_requirements = active_stack.requirements()
```

### Integration requirements

For all integrations that you use in your pipeline, you need to have their dependencies installed too. You can get a list of them in the following way:

```python
from zenml.integrations.registry import integration_registry
from zenml.integrations.constants import HUGGINGFACE, PYTORCH

# define a list of all required integrations
required_integrations = [PYTORCH, HUGGINGFACE]

# Generate requirements for all required integrations
integration_requirements = set(
    itertools.chain.from_iterable(
        integration_registry.select_integration_requirements(
            integration_name=integration,
            target_os=OperatingSystemType.LINUX,
        )
        for integration in required_integrations
    )
)
```

### Any project-specific requirements

For any other dependencies that your project relies on, you can then install all of these different requirements through a line in your `Dockerfile` that looks like the following. It assumes you have accumulated all the requirements in one file.

```Dockerfile
RUN pip install <ANY_ARGS> -r FILE
```

### Any system packages

If you have any `apt` packages that are needed for your application to function, be sure to include them too. This can be achieved in a `Dockerfile` as follows:

```Dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends YOUR_APT_PACKAGES
```

### Your project code files

The files containing your pipeline and step code and all other necessary functions should be available in your execution environment.

- If you have a [code repository](../../../user-guide/production-guide/connect-code-repository.md) registered, you don't need to include your code files in the image yourself. ZenML will download them from the repository to the appropriate location in the image.

- If you don't have a code repository but `allow_download_from_artifact_store` is set to `True` in your `DockerSettings` (`True` by default), ZenML will upload your code to the artifact store and make it available to the image.

- If both of these options are disabled, you can include your code files in the image yourself. This approach is not recommended and you should use one of the above options.

Take a look at [which files are built into the image](./which-files-are-built-into-the-image.md) page to learn more about what to include. Make sure that your code is in the `/app` directory and that this is set as the active working directory.


{% hint style="info" %}
Note that you also need Python, `pip` and `zenml` installed in your image.
{% endhint %}

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
