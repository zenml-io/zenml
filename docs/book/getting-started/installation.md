---
description: Installing ZenML and getting started.
icon: cauldron
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Installation

{% stepper %}
{% step %}
#### Install ZenML

ZenML currently supports **Python 3.10, 3.11, 3.12, and 3.13**. Please make sure that you are using a supported Python version.

{% tabs %}
{% tab title="Base package" %}
**ZenML** is a Python package that can be installed using `pip` or other Python package managers:

```shell
pip install zenml
```

{% hint style="warning" %}
Installing the base package only allows you to connect to a [deployed ZenML server](./deploying-zenml/). If you want to use ZenML purely locally, install it with the `local` extra:
```shell
pip install 'zenml[local]'
```
{% endhint %}
{% endtab %}

{% tab title="Local Dashboard" %}
If you want to use the [ZenML dashboard](https://github.com/zenml-io/zenml-dashboard) locally, you need to install ZenML with the `server` extra: 

```shell
pip install 'zenml[server]'
```

{% hint style="warning" %}
If you want to run a local server while running on a Mac with Apple Silicon (M1, M2, M3, M4), you should set the following environment variable:
```bash
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
```
You can read more about this [here](http://sealiesoftware.com/blog/archive/2017/6/5/Objective-C_and_fork_in_macOS_1013.html).
{% endhint %}

{% endtab %}

{% tab title="Jupyter Notebooks" %}
If you write your ZenML pipelines ins Jupyter notebooks, we recommend installing ZenML with the `jupyter` extra which includes improved CLI output and logs:

```shell
pip install 'zenml[jupyter]'
```

{% endtab %}

{% endtabs %}
{% endstep %}

{% step %}
#### Verifying Installations

Once the installation is completed, you can check whether the installation was successful either through Bash or Python:

{% tabs %}
{% tab title="Bash" %}
```bash
zenml version
```
{% endtab %}

{% tab title="Python" %}
```python
import zenml

print(zenml.__version__)
```
{% endtab %}
{% endtabs %}

If you would like to learn more about the current release, please visit our [PyPi package page.](https://pypi.org/project/zenml)
{% endstep %}
{% endstepper %}

## Running with Docker

`zenml` is also available as a Docker image hosted publicly on [DockerHub](https://hub.docker.com/r/zenmldocker/zenml). Use the following command to get started in a bash environment with `zenml` available:

```shell
docker run -it zenmldocker/zenml /bin/bash
```

If you would like to run the ZenML server with Docker:

```shell
docker run -it -d -p 8080:8080 zenmldocker/zenml-server
```

## Starting the local server

By default, ZenML runs without a server connected to a local database on your machine. If you want to access the dashboard locally, you need to start a local server:

```shell
# Make sure to have the `server` extra installed
pip install "zenml[server]"
zenml login --local  # opens the dashboard locally 
```

However, advanced ZenML features are dependent on a centrally deployed ZenML server accessible to other MLOps stack components. You can read more about it [here](deploying-zenml/). For the deployment of ZenML, you have the option to either [self-host](deploying-zenml/) it or register for a free [ZenML Pro](https://zenml.io/pro?utm_source=docs\&utm_medium=referral_link\&utm_campaign=cloud_promotion\&utm_content=signup_link) account.