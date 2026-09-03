---
description: Installing ZenML and getting started.
icon: cauldron
---

# Installation

{% stepper %}
{% step %}
#### Install ZenML

ZenML currently supports **Python 3.10, 3.11, 3.12, 3.13, and 3.14**. Please make sure that you are using a supported Python version.

Open a terminal and run:

```shell
curl -fsSL https://zenml.io/install | bash
```

That one command:

1. Installs [uv](https://docs.astral.sh/uv/) if you do not have it. No system Python and no `sudo` are needed.
2. Installs `zenml[local]`. Run inside a Python project (a `pyproject.toml` or `uv.lock` in the current directory) it adds ZenML to that project's environment with `uv add`, so your pipelines and ZenML share one set of dependencies. Run anywhere else it installs an isolated `zenml` CLI on your PATH.
3. Installs the [ZenML coding-agent skills](https://github.com/zenml-io/skills) into `~/.agents/skills`, plus `~/.claude/skills` and `~/.codex/skills` when Claude Code or Codex is installed.
4. Prints what to do next and stops:

```
zenml init             mark this directory as a ZenML repository
zenml login --local    local server and dashboard on this machine
zenml login            managed cloud. 14-day free trial
```

(Inside a project ZenML is not on your PATH, hence the printed commands read `uv run zenml ...`. The isolated install uses plain `zenml`.)

Works on macOS, Linux, WSL, and Git Bash on Windows. Running it again upgrades.

{% hint style="info" %}
**Want the local dashboard?** `zenml login --local` needs the `server` extra. Add `--server` to the installer (`curl -fsSL https://zenml.io/install | bash -s -- --server`) and it installs `zenml[server]` instead of `zenml[local]`. On Apple Silicon also set `export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES` before starting the server (see the Local Dashboard tab below).
{% endhint %}

| Option | Effect |
| --- | --- |
| `--server` | Install `zenml[server]` so `zenml login --local` can run the server and dashboard here |
| `--version 0.96.3` | Pin a ZenML release (`--pre` allows pre-releases) |
| `--with PKG` | Also install a package into the same environment (repeatable), e.g. an integration |
| `--project` / `--global` | Force the in-project or the isolated install |
| `--no-skills` | Skip the coding-agent skills |
| `--no-modify-path` | Leave your shell rc files alone (isolated install) |

Options go after `bash -s --`, so `curl -fsSL https://zenml.io/install | bash -s -- --help` lists everything, with environment-variable equivalents.

**Prefer to do it by hand?** Inside your project, the installer is equivalent to:

```shell
uv add "zenml[local]"                  # or "zenml[server]" for the local dashboard
npx skills add zenml-io/skills         # the coding-agent skills
uv run zenml init
```

If you prefer to manage the installation yourself with `pip` or another Python package manager:

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

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
