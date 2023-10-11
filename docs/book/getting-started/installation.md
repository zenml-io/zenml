---
description: Installing ZenML and getting started.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# 🧙 Installation

**ZenML** is a Python package that can be installed directly via `pip`:

```shell
pip install zenml
```

{% hint style="warning" %}
Note that ZenML currently supports **Python 3.7, 3.8, 3.9, and 3.10**. Please make sure that you are using a
supported Python version.
{% endhint %}

## Install with the dashboard

ZenML comes bundled with a web dashboard that lives inside
a [sister repository](https://github.com/zenml-io/zenml-dashboard). In order to get access to the dashboard **locally**,
you need to launch the [ZenML Server and Dashboard locally](/docs/book/platform-guide/set-up-your-mlops-platform/deploy-zenml/deploy-zenml.md).
For this, you need to install the optional dependencies for the ZenML Server:

```shell
pip install "zenml[server]"
```

{% hint style="info" %}
We highly encourage you to install ZenML in a virtual environment. At ZenML, We like to
use [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/)
or [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv) to manage our Python virtual environments.
{% endhint %}

## Verifying installations

Once the installation is completed, you can check whether the installation was successful either through Bash:

```bash
zenml version
```

or through Python:

```python
import zenml

print(zenml.__version__)
```

If you would like to learn more about the current release, please visit our
[PyPi package page.](https://pypi.org/project/zenml)

## Running with Docker

`zenml` is also available as a Docker image hosted publicly on [DockerHub](https://hub.docker.com/r/zenmldocker/zenml).
Use the following command to get started in a bash environment with `zenml` available:

```shell
docker run -it zenmldocker/zenml /bin/bash
```

If you would like to run the ZenML server with Docker:

```shell
docker run -it -d -p 8080:8080 zenmldocker/zenml-server
```
