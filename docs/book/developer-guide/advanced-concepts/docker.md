---
description: How ZenML uses Docker images to run your pipeline
---

Remote orchestrators and step operators build [Docker](https://www.docker.com/) images to 
run your pipeline code in an isolated and well-defined environment.
For this purpose, a [Dockerfile](https://docs.docker.com/engine/reference/builder/) is dynamically generated and used
to build the image using the local Docker client. This Dockerfile consists of the following steps:
* Starts from a base image which needs to have ZenML installed. By default, this will use the [official ZenML image](https://hub.docker.com/r/zenmldocker/zenml/) for the Python and ZenML version that you're using in the active Python environment. If you want to use a different image as the base for the following steps, check out [this guide](#using-a-custom-base-image).
* **Installs additional pip dependencies**. ZenML will automatically detect which integrations are used in your stack and install the required dependencies.
If your pipeline needs any additional requirements, check out our [guide on including custom dependencies](#how-to-install-additional-pip-dependencies).
* **Copies your active stack configuration**. This is needed so that ZenML can execute your code on the stack that you specified.
* **Copies your source files**. These files need to be included in the Docker image so ZenML can execute your step code. Check out [this section](#which-files-get-included) for more information on which files get included by default and how to exclude files.

## Using a custom base image

To have full control over the environment which is used to execute your pipelines,
you can specify a custom base image which will be used as the starting point of the 
Docker image that ZenML will use to execute your code. For more information on how 
to specify a base image for the [orchestrator](../../mlops_stacks/orchestrators/overview.md)
or [step operator](../../mlops_stacks/step_operators/overview.md) you're using, visit 
the corresponding documentation page.

{% hint style="info" %}
If you're going to use a custom base image, you need to make sure that it has Python, pip and 
ZenML installed for it to work.
{% endhint %}

## Which files get included

In order to execute your pipeline code inside the Docker image, ZenML needs to 
copy all your source code files that are necessary to execute the steps of your
pipeline.
ZenML will try to determine the root directory of your source files in the following order:
* If you've created a 
[ZenML repository](../stacks-profiles-repositories/stacks_profiles_repositories.md#repositories)
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
    @pipeline(dockerignore_file="/path/to/.dockerignore")
    def my_pipeline(...):
        ...
    ```
## How to install additional pip dependencies

If you want ZenML to install additional pip dependencies on top of the base image, you
can use any of the following three ways (or even combine them):
* Specify a list of [ZenML integrations]() that you're using in your pipeline:
    ```python
    from zenml.integrations.constants import PYTORCH, EVIDENTLY

    @pipeline(required_integrations=[PYTORCH, EVIDENTLY])
    def my_pipeline(...):
        ...
    ```
* Specify a list of pip requirements in code:
    ```python
    @pipeline(requirements=["torch==1.12.0", "torchvision"]))
    def my_pipeline(...):
        ...
    ```
* Specify a pip requirements file:
    ```python
    @pipeline(requirements="/path/to/requirements.txt")
    def my_pipeline(...):
        ...
    ```
