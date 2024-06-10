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
Note that ZenML currently supports **Python 3.8, 3.9, 3.10, and 3.11**. Please make sure that you are using a supported Python version.
{% endhint %}

## Install with the dashboard

ZenML comes bundled with a web dashboard that lives inside a [sister repository](https://github.com/zenml-io/zenml-dashboard). In order to get access to the dashboard **locally**, you need to launch the [ZenML Server and Dashboard locally](why-deploy-zenml/zenml-self-hosted/). For this, you need to install the optional dependencies for the ZenML Server:

```shell
pip install "zenml[server]"
```

{% hint style="info" %}
We highly encourage you to install ZenML in a virtual environment. At ZenML, We like to use [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/) or [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv) to manage our Python virtual environments.
{% endhint %}

## Nightly builds

ZenML also publishes nightly builds under the [`zenml-nightly` package name](https://pypi.org/project/zenml-nightly/). These are built from the latest [`develop` branch](https://github.com/zenml-io/zenml/tree/develop) (to which work ready for release is published) and are not guaranteed to be stable. To install the nightly build, run:

```shell
pip install zenml-nightly
```

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

If you would like to learn more about the current release, please visit our [PyPi package page.](https://pypi.org/project/zenml)

## Running with Docker

`zenml` is also available as a Docker image hosted publicly on [DockerHub](https://hub.docker.com/r/zenmldocker/zenml). Use the following command to get started in a bash environment with `zenml` available:

```shell
docker run -it zenmldocker/zenml /bin/bash
```

If you would like to run the ZenML server with Docker:

```shell
docker run -it -d -p 8080:8080 zenmldocker/zenml-server
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>

## Deploying the server

Though ZenML can run entirely as a pip package on a local system, its advanced features are dependent on a centrally-deployed ZenML server accessible to other MLOps stack components. You can read more about it [here](../getting-started/deploying-zenml/README.md).

For the deployment of ZenML, you have the option to either [self-host](why-deploy-zenml/zenml-self-hosted/) it or register for a free account on [ZenML Cloud](https://cloud.zenml.io/?utm\_source=docs\&utm\_medium=referral\_link\&utm\_campaign=cloud\_promotion\&utm\_content=signup\_link).
