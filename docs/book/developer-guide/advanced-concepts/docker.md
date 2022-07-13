---
description: How ZenML uses Docker images to run your pipeline
---

Remote orchestrators and step operators build [Docker](https://www.docker.com/) images to 
run your pipeline code in an isolated and well-defined environment.
For this purpose, a [Dockerfile](https://docs.docker.com/engine/reference/builder/) is dynamically generated and used
to build the image using the local Docker client. This Dockerfile consists of the following steps:
* Starts from a base image which needs to have ZenML installed. By default, this will use the [official ZenML image](https://hub.docker.com/r/zenmldocker/zenml/) for the Python and ZenML version that you're using in the current environment. If you want to use a different image as the base for the following steps, check out [this guide](#using-a-custom-base-image).
* **Installs additional pip dependencies**. ZenML will automatically detect which integrations are used in your stack and install the required dependencies.
If your pipeline needs any additional requirements, check out our [guide on including custom dependencies](#how-to-install-additional-pip-dependencies).
* **Copies your active stack configuration**. This is needed so that ZenML can execute your code on the stack that you specified.
* **Copies your source files**. These files need to be included in the Docker image so ZenML can execute your step code. Check out [this section](#which-files-get-included) for more information on which files get included by default and how to exclude files.

## Using a custom base image

## Which files get included

By default, all files in (root):
if ZenML repository exists, use this.
Otherwise the working directory is used.


https://docs.docker.com/engine/reference/builder/#dockerignore-file

Dockerignore in the ROOT.

You can also explicitly specify a `.dockerignore` file that you want to use:

```python
from zenml.pipelines import pipeline

@pipeline(dockerignore_file="/path/to/.dockerignore")
def my_pipeline(...):
    ...
```

## How to install additional pip dependencies

```python
from zenml.pipelines import pipeline

@pipeline(dockerignore_file=..., requirements=..., required_integrations=[])
def my_pipeline(...):
    ...
```
