---
icon: cauldron
description: Installing ZenML and getting started.
icon: cauldron
---

# Installation

**ZenML** is a Python package that can be installed directly via `pip`:

```shell
pip install zenml
```

{% hint style="warning" %}
Note that ZenML currently supports **Python 3.9, 3.10, 3.11 and 3.12**. Please make sure that you are using a supported Python version.
{% endhint %}

## Install with the dashboard

ZenML comes bundled with a web dashboard that lives inside a [sister repository](https://github.com/zenml-io/zenml-dashboard). In order to get access to the dashboard **locally**, you need to launch the [ZenML Server and Dashboard locally](deploying-zenml/). For this, you need to install the optional dependencies for the ZenML Server:

```shell
pip install "zenml[server]"
```

{% hint style="info" %}
We highly encourage you to install ZenML in a virtual environment. At ZenML, We like to use [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/) or [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv) to manage our Python virtual environments.
{% endhint %}

## Installing onto MacOS with Apple Silicon (M1, M2)

A change in how forking works on Macs running on Apple Silicon means that you should set the following environment variable which will ensure that your connections to the server remain unbroken:

```bash
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
```

You can read more about this [here](http://sealiesoftware.com/blog/archive/2017/6/5/Objective-C\_and\_fork\_in\_macOS\_1013.html). This environment variable is needed if you are working with a local server on your Mac, but if you're just using ZenML as a client / CLI and connecting to a deployed server then you don't need to set it.

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

Though ZenML can run entirely as a pip package on a local system, complete with the dashboard. You can do this easily:

```shell
pip install "zenml[server]"
zenml up  # opens the dashboard locally 
```

However, advanced ZenML features are dependent on a centrally-deployed ZenML server accessible to other MLOps stack components. You can read more about it [here](deploying-zenml/).

For the deployment of ZenML, you have the option to either [self-host](deploying-zenml/) it or register for a free [ZenML Pro](https://cloud.zenml.io/signup?utm\_source=docs\&utm\_medium=referral\_link\&utm\_campaign=cloud\_promotion\&utm\_content=signup\_link) account.
