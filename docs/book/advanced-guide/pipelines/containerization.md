---
description: How ZenML uses Docker images to run your pipeline
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


In the [Runtime Settings section](../../advanced-guide/pipelines/settings.md) of the docs, we saw how to
use the `BaseSettings` concept to configure ZenML in various ways. In this guide, we will dive deeper into
one particular sub-class of `BaseSettings` which is of particular important: `DockerSettings`. Here is why it is important.

When running locally, ZenML will execute the steps of your pipeline in the
active Python environment. When using remote [orchestrators](../../component-gallery/orchestrators/orchestrators.md)
or [step operators](../../component-gallery/step-operators/step-operators.md) instead,
ZenML builds [Docker](https://www.docker.com/) images to transport and
run your pipeline code in an isolated and well-defined environment.
For this purpose, a [Dockerfile](https://docs.docker.com/engine/reference/builder/) is dynamically generated and used
to build the image using the [image builder](../../component-gallery/image-builders/image-builders.md)
component of your stack. This Dockerfile consists of the following steps:

* Starts from a parent image which needs to have ZenML installed. By default, this will use the [official ZenML image](https://hub.docker.com/r/zenmldocker/zenml/) for the Python and ZenML version that you're using in the active Python environment. If you want to use a different image as the base for the following steps, check out [this guide](#using-a-custom-parent-image).
* **Installs additional pip dependencies**. ZenML will automatically detect which integrations are used in your stack and install the required dependencies.
If your pipeline needs any additional requirements, check out our [guide on including custom dependencies](#how-to-install-additional-pip-dependencies).
* **Copies your global configuration**. This is needed so that ZenML can connect to your [deployed ZenML instance](../../getting-started/deploying-zenml/deploying-zenml.md) to fetch the active stack and other required information.
* **Copies your source files**. These files need to be included in the Docker image so ZenML can execute your step code. Check out [this section](#which-files-get-included) for more information on which files get included by default and how to exclude files.
* **Sets user-defined environment variables.**

## Separate Docker images for different steps in your pipeline

In some cases the steps of your pipeline will have conflicting requirements or some
steps of your pipeline will require large dependencies that don't need to be installed
to run the remaining steps of your pipeline. For this case, ZenML allows you to specify
custom Docker settings for all steps of your pipeline and will build separate images if needed.

The following code examples on this page will display how to specify Docker settings for your pipeline,
but you can also specify specialized settings for some/all steps of your pipeline. Values specified
for a step will override the values defined on the pipeline that this step is contained in and can
be used to build specialized images for steps.

```python
docker_settings = DockerSettings(requirements=["tensorflow"])

@step(settings={"docker": docker_settings})
def my_training_step(...):
    ...
```

## Customizing the build process

The process explained above is all done automatically by ZenML and covers most basic use cases.
This section covers all the different ways in which you can hook into the Docker build
process to customize the resulting image to your needs.

For a full list of configuration options, check out
[our API Docs](https://apidocs.zenml.io/latest/core_code_docs/core-config/#zenml.config.docker_settings.DockerSettings).

For the configuration examples described below, you'll need to import the `DockerSettings` class:
```python
from zenml.config import DockerSettings
```

### Which files get included

ZenML will try to determine the root directory of your source files in the following order:
* If you've created a 
[ZenML repository](../../starter-guide/stacks/stacks.md)
for your project, the repository directory will be used.
* Otherwise, the parent directory of the python file you're executing will be the source root.
For example, running `python /path/to/file.py`, the source root would be `/path/to`.

By default, ZenML will copy all contents of this root directory into the Docker image.
If you want to exclude files to keep the image smaller, you can do so using a [.dockerignore
file](https://docs.docker.com/engine/reference/builder/#dockerignore-file) in either of the 
following two ways:

* Have a file called `.dockerignore` in your source root directory explained above.
* Explicitly specify a `.dockerignore` file that you want to use:
    ```python
    docker_settings = DockerSettings(dockerignore="/path/to/.dockerignore")
    
    @pipeline(settings={"docker": docker_settings})
    def my_pipeline(...):
        ...
    ```

#### Don't include any user files

If you want to prevent ZenML from copying any of your source files, you can do so by
setting the `copy_files` attribute on the Docker settings to `False`:
```python
docker_settings = DockerSettings(copy_files=False)

@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

{% hint style="warning" %}
This is an advanced feature and will most likely cause unintended and unanticipated behavior
when running your pipelines. If you use this, make sure to copy all the necessary files
to the correct paths yourself.
{% endhint %}

#### Don't include the global configuration

If you want to prevent ZenML from copying your global configuration,
you can do so by setting the `copy_global_config` attribute on the Docker
settings to `False`:
```python
docker_settings = DockerSettings(copy_global_config=False)

@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

{% hint style="warning" %}
This is an advanced feature and will most likely cause unintended and unanticipated
behavior when running your pipelines. If you use this, make sure to copy the global configuration
to the correct path yourself.
{% endhint %}

### How to install additional pip dependencies or apt packages

By default, ZenML will automatically install all the packages required by your
active ZenML stack. There are, however, various ways in which you can specify
additional packages that should be installed:

* Install all the packages in your local python environment (This will use the `pip` or `poetry`
package manager to get a list of your local packages):
    ```python
    # or use "poetry_export"
    docker_settings = DockerSettings(replicate_local_python_environment="pip_freeze")

    @pipeline(settings={"docker": docker_settings})
    def my_pipeline(...):
        ...
    ```

    If required, a custom command can be provided. This command has to output a list of requirements
    following the format of the [requirements file](https://pip.pypa.io/en/stable/reference/requirements-file-format/):

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
* Specify a list of pip requirements in code:
    ```python
    docker_settings = DockerSettings(requirements=["torch==1.12.0", "torchvision"])

    @pipeline(settings={"docker": docker_settings})
    def my_pipeline(...):
        ...
    ```
* Specify a pip requirements file:
    ```python
    docker_settings = DockerSettings(requirements="/path/to/requirements.txt")

    @pipeline(settings={"docker": docker_settings})
    def my_pipeline(...):
        ...
    ```
* Specify a list of [ZenML integrations](../../component-gallery/integrations.md) that you're using in your pipeline:
    ```python
    from zenml.integrations.constants import PYTORCH, EVIDENTLY

    docker_settings = DockerSettings(required_integrations=[PYTORCH, EVIDENTLY])

    @pipeline(settings={"docker": docker_settings})
    def my_pipeline(...):
        ...
    ```
* Specify a list of apt packages in code:
    ```python
    docker_settings = DockerSettings(apt_packages=["git"])

    @pipeline(settings={"docker": docker_settings})
    def my_pipeline(...):
        ...
    ```
* Prevent ZenML from automatically installing the requirements of your stack:
    ```python
    docker_settings = DockerSettings(install_stack_requirements=False)

    @pipeline(settings={"docker": docker_settings})
    def my_pipeline(...):
        ...
    ```

You can even combine these methods, but do make sure that your
list of pip requirements doesn't overlap with the ones specified by your required integrations.
See our recommended [best practices](../../guidelines/best-practices.md) for more tips.

Depending on all the options specified in your Docker settings, ZenML will install the requirements
in the following order (each step optional):

- The packages installed in your local python environment
- The packages specified via the `requirements` attribute
- The packages specified via the `required_integrations` and potentially stack requirements

## Using a custom parent image

By default, ZenML will perform all the steps described above on top of the
[official ZenML image](https://hub.docker.com/r/zenmldocker/zenml/) for the Python
and ZenML version that you're using in the active Python environment. To have more
control over the entire environment which is used to execute your pipelines,
you can either specify a custom pre-built parent image or a Dockerfile which ZenML will use to
build a parent image for you.

{% hint style="info" %}
If you're going to use a custom parent image (either pre-built or by specifying a Dockerfile),
you need to make sure that it has Python, pip and ZenML installed for it to work. If you need 
a starting point, you can take a look at the Dockerfile that ZenML uses
[here](https://github.com/zenml-io/zenml/blob/main/docker/base.Dockerfile).
{% endhint %}

### Using a pre-built parent image

If you want to use a static parent image (which for example has some internal dependencies installed)
that doesn't need to be rebuilt on every pipeline run, you can do so by specifying it on the
Docker settings for your pipeline:

```python
docker_settings = DockerSettings(parent_image="my_registry.io/image_name:tag")

@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

If you want to use this image directly to run your steps without
including any code or installing any requirements on top of it,
you can skip the Docker builds by specifying it in the Docker
settings:

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
This is an advanced feature and will most likely cause unintended and unanticipated behavior
when running your pipelines. If you use this, make sure your code files and global configuration
are correctly included in the image you specified.
{% endhint %}

### Specifying a Dockerfile to dynamically build a parent image

In some cases you might want full control over the resulting Docker image but want
to build a Docker image dynamically each time a pipeline is executed. To make this process easier,
ZenML allows you to specify a custom Dockerfile as well as build context directory and
build options. ZenML then builds an intermediate image based on the Dockerfile you specified and uses
the intermediate image as the parent image.

{% hint style="info" %}
Depending on the configuration of your Docker settings, this intermediate image
might also be used directly to execute your pipeline steps.
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

## Customizing the build environment

The [image builder](../../component-gallery/image-builders/image-builders.md) component
of your stack defines the environment in which the Docker build with the previously
described Dockerfile gets executed. This could be either on your local machine
(when using the [local image builder](../../component-gallery/image-builders/local.md))
or in some remote environment. Check our the image builder documentation for more information.

## Building Docker images without running the pipeline

Whenever you run a pipeline on a stack that requires Docker images, ZenML will automatically build these
images for you to make sure your pipeline can be executed. If you want to run this build step separately
without actually running the pipeline, you can do so by calling `pipeline_instance.build(...)` in Python
or using the CLI command `zenml pipeline build`. This will register the build output in the ZenML
database and allow you to use the built images when running a pipeline later.
To use a registered build when running a pipeline, pass it as an argument in Python
```python
pipeline_instance.run(build=<BUILD_ID>)
```

or when running a pipeline from the CLI

```bash
zenml pipeline run <PIPELINE_NAME> --build=<BUILD_ID>
```

{% hint style="warning" %}
Building Docker images currently includes your step code, which means specifying a custom build when
running a pipeline will not run the code that you have on your client machine, but will instead use
the code that is included in the Docker images of the build.
{% endhint %}
