---
description: Using Docker images to run your pipeline.
---

# Containerize your pipeline



## Define where an image is built

TODO: Include reference to managing envioronments and maybe move to the top [managing environments](manage-environments.md)

## Reusing Docker images

Link to [code repository](connect-your-git-repository.md)

## Customize the Docker building

When running locally, ZenML will sequentially execute the steps of your pipeline in the active Python environment. However, when using remote [orchestrators](broken-reference/) or [step operators](broken-reference/), ZenML will build [Docker](https://www.docker.com/) images which are used to run your pipeline code in an isolated and well-defined environment.

For this purpose, a [Dockerfile](https://docs.docker.com/engine/reference/builder/) is dynamically generated at runtime. It is then used to build the docker image using the [image builder](manage-environments.md) component of your stack. The Dockerfile consists of the following steps:

* **Starts from a parent image** that has **ZenML installed**. By default, this will use the [official ZenML image](https://hub.docker.com/r/zenmldocker/zenml/) for the Python and ZenML version that you're using in the active Python environment. If you want to use a different image as the base for the following steps, check out [this guide](containerize-your-pipeline.md#using-a-custom-parent-image).
* **Installs additional pip dependencies**. ZenML will automatically detect which integrations are used in your stack and install the required dependencies. If your pipeline needs any additional requirements, check out our [guide on including custom dependencies](containerize-your-pipeline.md#how-to-install-additional-pip-dependencies).
* **Optionally copies your source files**. Your source files need to be available inside the Docker container so ZenML can execute your step code. Check out [this section](containerize-your-pipeline.md#handling-source-files) for more information on how you can customize how ZenML handles your source files in Docker images.
* **Sets user-defined environment variables.**

The process described above is automated by ZenML and covers most basic use cases. This section covers various ways to customize the Docker build process to fit your needs.

For a full list of configuration options, check out [our API Docs](https://apidocs.zenml.io/latest/core\_code\_docs/core-config/#zenml.config.docker\_settings.DockerSettings).

For the configuration examples described below, you'll need to import the `DockerSettings` class:

```python
from zenml.config import DockerSettings
```

### Handling source files

ZenML determines the root directory of your source files in the following order:

* If you've created a [ZenML repository](broken-reference/) for your project, the repository directory will be used.
* Otherwise, the parent directory of the python file you're executing will be the source root. For example, running `python /path/to/file.py`, the source root would be `/path/to`.

You can specify how these files are handled using the `source_files` attribute on the `DockerSettings`:

* The default behavior `download_or_include`: The files will be downloaded if they're inside a registered [code repository](broken-reference/) and the repository has no local changes, otherwise, they will be included in the image.
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

If required, a custom command can be provided. This command must output a list of requirements following the format ofthe [requirements file](https://pip.pypa.io/en/stable/reference/requirements-file-format/):

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

*   Specify a list of pip requirements in code:

    ```python
    docker_settings = DockerSettings(requirements=["torch==1.12.0", "torchvision"])

    @pipeline(settings={"docker": docker_settings})
    def my_pipeline(...):
        ...
    ```
*   Specify a pip requirements file:

    ```python
    docker_settings = DockerSettings(requirements="/path/to/requirements.txt")

      @pipeline(settings={"docker": docker_settings})
      def my_pipeline(...):
          ...
    ```
* Specify a list of [ZenML integrations](broken-reference/) that you're using in your pipeline:

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
You can combine these methods but do make sure that your list of pip requirements does not overlap with the ones specified explicitly in the docker settings.
{% endhint %}

Depending on the options specified in your Docker settings, ZenML installs the requirements in the following order (each step optional):

* The packages installed in your local Python environment
* The packages specified via the `requirements` attribute (step level overwrites pipeline level)
* The packages specified via the `required_integrations` and potentially stack requirements

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
