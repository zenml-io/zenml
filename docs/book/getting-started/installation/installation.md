---
description: How to install ZenML
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Installation (Python Package)

**ZenML** is a Python package that can be installed directly via `pip`:

```shell
pip install zenml
```

{% hint style="warning" %}
Please note that ZenML currently only supports Python 3.7, 3.8, 3.9 and 3.10.
Please adjust your Python environment accordingly.
{% endhint %}

ZenML comes bundled with a React-based dashboard that lives inside a [sister repository](https://github.com/zenml-io/zenml-dashboard). In order to get access to the dashboard locally, you need to launch the [ZenML Server and Dashboard locally](../deploying-zenml/deploying-zenml.md). For this, you need to install the optional dependencies for the ZenML Server:

```shell
pip install "zenml[server]"
```

## Virtual Environments

We highly encourage you to install ZenML in a virtual environment.
At ZenML, We like to use 
[virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/)
or [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv)
to manage our Python virtual environments.

As mentioned above, make sure that your virtual environment uses one of the
supported Python versions.

## Verifying Installations

Once the installation is completed, you can check whether the installation was successful through:

### Bash

```bash
zenml version
```

### Python

```python
import zenml
print(zenml.__version__)
```

If you would like to learn more about the current release, please visit our 
[PyPi package page.](https://pypi.org/project/zenml)

## Running with Docker

### Python package

`zenml` is also available as a Docker image hosted publicly on 
[DockerHub](https://hub.docker.com/r/zenmldocker/zenml). 
Use the following command to get started in a bash environment with `zenml` available:

```shell
docker run -it zenmldocker/zenml /bin/bash
```

### ZenML Server

If you would like to run the ZenML server with Docker:

```shell
docker run -it -d -p 8080:8080 zenmldocker/zenml-server
```

## Installing Develop

If you want to use the bleeding edge of ZenML that has not even been released
yet, you can install our `develop` branch directly.

Installing develop is mainly useful if there are key features or bug fixes that
you urgently need so you can get those immediately and do not have to wait
for the next release.

{% hint style="warning" %}
As the name suggests, the new features in the `develop` branch are still under
development and might not be as polished as the final released version.

Use at your own risk; no guarantees given!
{% endhint %}

```bash
pip install git+https://github.com/zenml-io/zenml.git@develop --upgrade
```

### Using develop with Remote Orchestrators

Remote orchestrators like [Kubeflow](../../component-gallery/orchestrators/kubeflow.md)
require [Docker Images](../../getting-started/deploying-zenml/docker.md) to set up the
environments of each step. By default, they use the official ZenML docker image
that we provide with each release. However, if you install from develop, this
image will be outdated, so you need to build a custom image instead, and
specify it in the configuration of your orchestrator accordingly (see the 
[MLOps Stacks Orchestrator](../../component-gallery/orchestrators/orchestrators.md) 
page of your specific orchestrator flavor for more details on how this can be 
done).

#### Building Custom Docker Images

To build a custom image, you first need to
[install Docker](https://docs.docker.com/engine/install/), then run one of the
following commands from the ZenML repo root depending on your operating system:

##### Linux, MacOS (Intel), Windows

```
docker build -t <IMAGE_NAME> -f docker/local-dev.Dockerfile .
```

##### MacOS (M1)

```
docker build --platform linux/amd64 -t <IMAGE_NAME> -f docker/local-dev.Dockerfile .
```
