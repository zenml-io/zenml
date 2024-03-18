---
description: Using Docker images to run your pipeline.
---

# Containerize your pipeline

ZenML executes pipeline steps sequentially in the active Python environment when running locally. However, with remote [orchestrators](../../../stacks-and-components/component-guide/orchestrators/orchestrators.md) or [step operators](../../../stacks-and-components/component-guide/step-operators/step-operators.md), ZenML builds [Docker](https://www.docker.com/) images to run your pipeline in an isolated, well-defined environment.

There are three ways to control this containerization process:

* [Define where an image is built](containerize-your-pipeline.md#define-where-an-image-is-built)
* [Reuse Docker image builds from previous runs](containerize-your-pipeline.md#reuse-docker-image-builds-from-previous-runs)
* [Customize what gets built into the image](containerize-your-pipeline.md#customize-the-docker-building)

## Define where an image is built

[Image builders](../../../stacks-and-components/component-guide/image-builders/image-builders.md) determine how and where an image is built. Learn more [here](understanding-environments.md#image-builder-environment).

## Reuse Docker image builds from previous runs

ZenML automatically [builds and pushes Docker images](understanding-environments.md#execution-environments) when running a pipeline on a stack requiring Docker images. To run this build step separately without running the pipeline, call:

```python
my_pipeline.build(...)
```

in Python or using the CLI command:

```shell
# If running the first time, register pipeline to get name and ID
zenml pipeline register [OPTIONS] my_module.my_pipeline

# Build docker images using the image builder defined in the stack and push to the container registry defined in the stack
zenml pipeline build [OPTIONS] PIPELINE_NAME_OR_ID
```

You can see all pipeline builds with the command:

This will register the build output in the ZenML database and allow you to use the built images when running a pipeline later.

```bash
zenml pipeline builds list
```

To use a registered build when running a pipeline, pass it as an argument in Python

```python
my_pipeline = my_pipeline.with_options(build=<BUILD_ID>)
```

or when running a pipeline from the CLI

```bash
zenml pipeline run <PIPELINE_NAME> --build=<BUILD_ID>
```

### Automate build reuse by connecting a code repository

Building Docker images without [connecting a git repository](../../production-guide/connect-code-repository.md) includes your step code. This means specifying a custom build when running a pipeline will **not run the code on your client machine** but will use the code **included in the Docker images of the build**. This allows you to make local code changes, but reusing a build from before will _always_ execute the code bundled in the Docker image, rather than the local code. This is why you also have to explicitly specify the `build_id` when running a pipeline.

To avoid this, disconnect your code from the build by [connecting a git repository](../configuring-zenml/connect-your-git-repository.md). Registering a code repository lets you avoid building images each time you run a pipeline and quickly iterate on your code. Also, ZenML will automatically figure out which builds match your pipeline and reuse the appropriate execution environment. This approach is highly recommended. Read more [here](../../production-guide/connect-code-repository.md).

## Customize the Docker building

When a [pipeline is run with a remote orchestrator](understanding-environments.md) a [Dockerfile](https://docs.docker.com/engine/reference/builder/) is dynamically generated at runtime. It is then used to build the docker image using the [image builder](understanding-environments.md#image-builder-environment) component of your stack. The Dockerfile consists of the following steps:

* **Starts from a parent image** that has **ZenML installed**. By default, this will use the [official ZenML image](https://hub.docker.com/r/zenmldocker/zenml/) for the Python and ZenML version that you're using in the active Python environment. If you want to use a different image as the base for the following steps, check out [this guide](containerize-your-pipeline.md#using-a-custom-parent-image).
* **Installs additional pip dependencies**. ZenML will automatically detect which integrations are used in your stack and install the required dependencies. If your pipeline needs any additional requirements, check out our [guide on including custom dependencies](containerize-your-pipeline.md#installing-additional-pip-dependencies-or-apt-packages).
* **Optionally copies your source files**. Your source files need to be available inside the Docker container so ZenML can execute your step code. Check out [this section](containerize-your-pipeline.md#handling-source-files) for more information on how you can customize how ZenML handles your source files in Docker images.
* **Sets user-defined environment variables.**

The process described above is automated by ZenML and covers the most basic use cases. This section covers various ways to customize the Docker build process to fit your needs.

For a full list of configuration options, check out [our API Docs](https://sdkdocs.zenml.io/latest/core\_code\_docs/core-config/#zenml.config.docker\_settings.DockerSettings).

### How to configure Docker builds for your pipelines

Customizing the Docker builds for your pipelines and steps is done using the `DockerSettings` class which you can import like this:

```python
from zenml.config import DockerSettings
```

There are many ways in which you can supply these settings:

* Configuring them on a pipeline applies the settings to all steps of that pipeline:

```python
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

* Using a YAML configuration file as described [here](../pipelining-features/configure-steps-pipelines.md#method-3-configuring-with-yaml):

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

Check out [this page](../pipelining-features/pipeline-settings.md#hierarchy-and-precedence) for more information on the hierarchy and precedence of the various ways in which you can supply the settings.

### Handling source files

ZenML determines the root directory of your source files in the following order:

* If you've initialized zenml (`zenml init`), the repository root directory will be used.
* Otherwise, the parent directory of the Python file you're executing will be the source root. For example, running `python /path/to/file.py`, the source root would be `/path/to`.

You can specify how these files are handled using the `source_files` attribute on the `DockerSettings`:

* The default behavior `download_or_include`: The files will be downloaded if they're inside a registered [code repository](connect-your-git-repository.md) and the repository has no local changes, otherwise, they will be included in the image.
* If you want your files to be included in the image in any case, set the `source_files` attribute to `include`.
* If you want your files to be downloaded in any case, set the `source_files` attribute to `download`. If this is specified, the files must be inside a registered code repository and the repository must have no local changes, otherwise the Docker build will fail.
* If you want to prevent ZenML from copying or downloading any of your source files, you can do so by setting the `source_files` attribute on the Docker settings to `ignore`. This is an advanced feature and will most likely cause unintended and unanticipated behavior when running your pipelines. If you use this, make sure to copy all the necessary files to the correct paths yourself.

**Which files get included**

When including files in the image, ZenML copies all contents of the root directory into the Docker image. To exclude files and keep the image smaller, use a [.dockerignore file](https://docs.docker.com/engine/reference/builder/#dockerignore-file) in either of the following ways:

* Have a file called `.dockerignore` in your source root directory.
*   Explicitly specify a `.dockerignore` file to use:

    ```python
    docker_settings = DockerSettings(dockerignore="/path/to/.dockerignore")

    @pipeline(settings={"docker": docker_settings})
    def my_pipeline(...):
        ...
    ```

### Installing additional pip dependencies or apt packages

By default, ZenML automatically installs all packages required by your active ZenML stack. However, you can specify additional packages to be installed in various ways:

* Install all the packages in your local Python environment (This will use the `pip` or `poetry` package manager to get a list of your local packages):

```python
# or use "poetry_export"
docker_settings = DockerSettings(replicate_local_python_environment="pip_freeze")


@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

If required, a custom command can be provided. This command must output a list of requirements following the format of the [requirements file](https://pip.pypa.io/en/stable/reference/requirements-file-format/):

```python
docker_settings = DockerSettings(replicate_local_python_environment=[
    "poetry",
    "export",
    "--extras=train",
    "--format=requirements.txt"
])


@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

*   Specify a list of requirements in code:

    ```python
    docker_settings = DockerSettings(requirements=["torch==1.12.0", "torchvision"])

    @pipeline(settings={"docker": docker_settings})
    def my_pipeline(...):
        ...
    ```
*   Specify a requirements file:

    ```python
    docker_settings = DockerSettings(requirements="/path/to/requirements.txt")

    @pipeline(settings={"docker": docker_settings})
    def my_pipeline(...):
        ...
    ```
* Specify a list of [ZenML integrations](../../../stacks-and-components/component-guide/component-guide.md) that you're using in your pipeline:

```python
from zenml.integrations.constants import PYTORCH, EVIDENTLY

docker_settings = DockerSettings(required_integrations=[PYTORCH, EVIDENTLY])


@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

*   Specify a list of apt packages in code:

    ```python
    docker_settings = DockerSettings(apt_packages=["git"])

    @pipeline(settings={"docker": docker_settings})
    def my_pipeline(...):
        ...
    ```
*   Prevent ZenML from automatically installing the requirements of your stack:

    ```python
    docker_settings = DockerSettings(install_stack_requirements=False)

      @pipeline(settings={"docker": docker_settings})
      def my_pipeline(...):
          ...
    ```
* In some cases the steps of your pipeline will have conflicting requirements or some steps of your pipeline will require large dependencies that don't need to be installed to run the remaining steps of your pipeline. For this case, ZenML allows you to specify custom Docker settings for steps in your pipeline.

```python
docker_settings = DockerSettings(requirements=["tensorflow"])


@step(settings={"docker": docker_settings})
def my_training_step(...):
    ...
```

{% hint style="info" %}
You can combine these methods but do make sure that your list of requirements does not overlap with the ones specified explicitly in the Docker settings.
{% endhint %}

Depending on the options specified in your Docker settings, ZenML installs the requirements in the following order (each step optional):

* The packages installed in your local Python environment
* The packages specified via the `requirements` attribute (step level overwrites pipeline level)
* The packages specified via the `required_integrations` and potentially stack requirements

* **Experimental**: If you want to use [`uv`](https://github.com/astral-sh/uv) for faster resolving and installation of your Python packages, you can use by it as follows:

```python
docker_settings = DockerSettings(python_package_installer="uv")

@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```
{% hint style="info" %}
`uv` is a relatively new project and not as stable as `pip` yet, which might lead to errors during package installation.
If this happens, try switching the installer back to `pip` and see if that solves the issue.
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
This is an advanced feature and may cause unintended behavior when running your pipelines. If you use this, ensure your code files are correctly included in the image you specified.
{% endhint %}

#### Specifying a Dockerfile to dynamically build a parent image

In some cases, you might want full control over the resulting Docker image but want to build a Docker image dynamically each time a pipeline is executed. To make this process easier, ZenML allows you to specify a custom Dockerfile as well as `build context` directory and build options. ZenML then builds an intermediate image based on the Dockerfile you specified and uses the intermediate image as the parent image.

{% hint style="info" %}
Depending on the configuration of your Docker settings, this intermediate image might also be used directly to execute your pipeline steps.
{% endhint %}

```python
docker_settings = DockerSettings(
    dockerfile="/path/to/dockerfile",
    build_context_root="/path/to/build/context",
    build_options=...
)


@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
