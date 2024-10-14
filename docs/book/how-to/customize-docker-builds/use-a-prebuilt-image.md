# Skip building an image on every pipeline run

When running a pipeline on a remote Stack, ZenML builds a Docker image with a base ZenML image and adds all of your project dependencies and your pipeline code to it. This process might take significant time depending on how big your dependencies are, how powerful your local system is and how fast your internet connection is (to pull base layers and push the final image to your container registry). 

To save time and costs, you can choose to not build a Docker image every time your pipeline runs. This guide shows you how to do it using a pre-built image, what you should include in your image for the pipeline to run successfully and other tips.

{% hint style="info" %}
Note that using this feature means that you won't be able to leverage any updates you make to your code or dependencies, outside of what your image already contains.
{% endhint %}

The DockerSettings class in ZenML allows you to set a parent image to be used in your pipeline runs and the ability to skip building an image on top of it. This approach works in two ways:
- [If ZenML built an image for your pipeline previously](#if-zenml-built-an-image-for-your-pipeline-previously)
- [If ZenML has never built an image for your pipeline](#if-zenml-has-never-built-an-image-for-your-pipeline)

## If ZenML built an image for your pipeline previously

This is the case where you have had a previous pipeline run where ZenML did build an image and pushed it your registry.

Here, you can just reuse the image by setting it to the `parent_image` attribute of the `DockerSettings` class and setting `skip_build` to `True`.

```python
docker_settings = DockerSettings(
    parent_image="my_registry.io/image_name:tag",
    skip_build=True
)


@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

On every subsequent pipeline run now, ZenML will just use the code and the dependencies that were a part of the pipeline run whose image you are now using. This approach works without you having to worry about what goes in the image since ZenML built it in the first place.


## If ZenML has never built an image for your pipeline

This is the case where you are running a pipeline for the first time with ZenML and don't want ZenML to build an image for you. Here, you will have to provide an image to the `parent_image` attribute which already has all of your code and the right dependencies installed.

{% hint style="info" %}
Note that this is different from the case where you [only specify a parent image](../../../../docs/book/how-to/customize-docker-builds/docker-settings-on-a-pipeline.md#using-a-pre-built-parent-image) and don't want to `skip_build`. In the latter, ZenML still builds the image but does it on top of your parent image and not the base ZenML image.
{% endhint %}

### What should your image contain

It is crucial that you ensure that all of your code files and dependencies are included in the image you provide to `DockerSettings` as parent image. This is because ZenML expects to be able to execute this image right away, without any modifications, to run your pipeline steps.

The following points are derived from how ZenML builds an image internally and will help you make your own images:

#### Your stack requirements

A ZenML Stack can have different tools and each comes with its own requirements. You need to ensure that your image contains them. The following is how you can get a list of stack requirements.

```python
from zenml.client import Client

stack_name = <YOUR_STACK>
# set your stack as active if it isn't already
Client().set_active_stack(stack_name)

# get the requirements for the active stack
active_stack = Client().active_stack
stack_requirements = active_stack.requirements()
```

#### Integration requirements

For all integrations that you use in your pipeline, you need to have their dependencies installed too. The following is how you can get a list of them.

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

#### Any project specific requirements

Any other dependencies that your project relies on. You can then install all of these different requirements through a line in your Dockerfile that looks like the following. It assumes you have accumulated all the requirements in one file.

```Dockerfile
RUN pip insatll <ANY_ARGS> -r FILE
```

#### Any system packages

If you have any apt packages that are needed for your application to function, be sure to include them too. This can be achieved in a Dockerfile as follows:

```Dockerfile
RUN apt-get update && apt-get install -y 
--no-install-recommends YOUR_APT_PACKAGES
```

{% hint style="info" %}
Note that you also need Python, pip and zenml installed in your image.
{% endhint %}


## Where you can use this feature

- One way to use this is when ZenML has already built an image for your code in a previous pipeline run and you want to reuse it in a new run. This saves you build times at the cost of not being able to leverage any updates you made to your code (or your dependencies) since then.
- Another use case is when you are running in an environment that either doesn't have docker installed or doesn't have enough memory to pull your base image and build a new image on top of it (think Codespaces or other CI/CD environments).
