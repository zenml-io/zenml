---
description: How to install ZenML
---

# Installation

**ZenML** is a Python package that can be installed directly via `pip`:
```
pip install zenml
```

{% hint style="warning" %}
Please note that ZenML currently only supports Python 3.7, 3.8, and 3.9.
Please adjust your Python environment accordingly.
{% endhint %}

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

## Running with Docker

`zenml` is also available as a Docker image hosted publicly on 
[DockerHub](https://hub.docker.com/r/zenmldocker/zenml). 
Use the following command to get started in a bash environment with `zenml` available:

```
docker run -it zenmldocker/zenml /bin/bash
```

## Known installation issues for M1 Mac Users

If you have a M1 Mac machine and you are encountering an error while trying to install ZenML, 
please try to setup `brew` and `pyenv` with Rosetta 2 and then install ZenML. The issue arises because some of the dependencies 
aren’t fully compatible with the vanilla ARM64 Architecture. The following links may be helpful (Thank you Reid Falconer!):

- [Pyenv with Apple Silicon](http://sixty-north.com/blog/pyenv-apple-silicon.html)
- [Install Python Under Rosetta 2](https://medium.com/thinknum/how-to-install-python-under-rosetta-2-f98c0865e012)
