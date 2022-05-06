---
description: How to install ZenML
---

# Installation


## Welcome

Your first step is to install **ZenML**, which comes bundled as a good old `pip` package.

{% hint style="warning" %}
Please note that we only support Python >= 3.7 <3.9, so please adjust your Python environment accordingly.
{% endhint %}

## Virtual Environment

We highly encourage you to install **ZenML** in a virtual environment. We like
to use [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/)
to manage our Python virtual environments.

## Install with pip

When you're set with your environment, run:

```bash
pip install zenml
```

Alternatively, if you’re feeling brave, feel free to install the bleeding edge: **NOTE:** Do so at your own risk;
no guarantees given!

```bash
pip install git+https://github.com/zenml-io/zenml.git@develop --upgrade
```

Once the installation is completed, you can check whether the installation was successful through:

## Bash

```bash
zenml version
```

## Python

```python
import zenml
print(zenml.__version__)
```

If you would like to learn more about the current release, please visit our 
[PyPi package page.](https://pypi.org/project/zenml)

## Running with Docker

`zenml` is available as a Docker image hosted publicly on [DockerHub](https://hub.docker.com/r/zenmldocker/zenml). Use the following command to get started in a bash environment with `zenml` available:

```
docker run -it zenmldocker/zenml /bin/bash
```

## Enabling auto-completion on the CLI


{% hint style="warning" %}
The following commands will only work if you have zenml installed in your global python env. If you are using 
virtual environments, you'll have to manually export the environment variable whenever you are using that env.
{% endhint %}

{% tabs %}
{% tab title="Bash" %}
For Bash, add this to `~/.bashrc`:
```bash
eval "$(_ZENML_COMPLETE=source_bash zenml)"
```
{% endtab %}

{% tab title="Zsh" %}
For Zsh, add this to `~/.zshrc`:

```bash
eval "$(_ZENML_COMPLETE=source_zsh zenml)"
```
{% endtab %}

{% tab title="Fish" %}
For Fish, add this to `~/.config/fish/completions/foo-bar.fish`:

```bash
eval (env _ZENML_COMPLETE=source_fish zenml)
```
{% endtab %}
{% endtabs %}