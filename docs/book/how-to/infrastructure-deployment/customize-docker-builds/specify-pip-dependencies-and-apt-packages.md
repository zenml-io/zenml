# Specify pip dependencies and apt packages

{% hint style="warning" %}
The configuration for specifying pip and apt dependencies only works in the remote pipeline case, and is disregarded for local pipelines (i.e. pipelines that run locally without having to build a Docker image).
{% endhint %}

When a [pipeline is run with a remote orchestrator](../configure-python-environments/README.md) a [Dockerfile](https://docs.docker.com/engine/reference/builder/) is dynamically generated at runtime. It is then used to build the Docker image using the [image builder](../configure-python-environments/README.md#-configure-python-environments) component of your stack.

For all of examples on this page, note that `DockerSettings` can be imported using `from zenml.config import DockerSettings`.

By default, ZenML automatically installs all packages required by your active ZenML stack. However, you can specify additional packages to be installed in various ways:

* Install all the packages in your local Python environment (This will use the `pip` or `poetry` package manager to get a list of your local packages):

```python
# or use "poetry_export"
docker_settings = DockerSettings(replicate_local_python_environment="pip_freeze")


@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

If required, a custom command can be provided. This command must output a list of requirements following the format of the [requirements file](https://pip.pypa.io/en/stable/reference/requirements-file-format/):

```python
from zenml.config import DockerSettings

docker_settings = DockerSettings(replicate_local_python_environment=[
    "poetry",
    "export",
    "--extras=train",
    "--format=requirements.txt"
])


@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

*   Specify a list of requirements in code:

    ```python
    docker_settings = DockerSettings(requirements=["torch==1.12.0", "torchvision"])

    @pipeline(settings={"docker": docker_settings})
    def my_pipeline(...):
        ...
    ```
*   Specify a requirements file:

    ```python
    docker_settings = DockerSettings(requirements="/path/to/requirements.txt")

    @pipeline(settings={"docker": docker_settings})
    def my_pipeline(...):
        ...
    ```
* Specify a list of [ZenML integrations](../../component-guide/README.md) that you're using in your pipeline:

```python
from zenml.integrations.constants import PYTORCH, EVIDENTLY

docker_settings = DockerSettings(required_integrations=[PYTORCH, EVIDENTLY])


@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

*   Specify a list of apt packages in code:

    ```python
    docker_settings = DockerSettings(apt_packages=["git"])

    @pipeline(settings={"docker": docker_settings})
    def my_pipeline(...):
        ...
    ```
*   Prevent ZenML from automatically installing the requirements of your stack:

    ```python
    docker_settings = DockerSettings(install_stack_requirements=False)

      @pipeline(settings={"docker": docker_settings})
      def my_pipeline(...):
          ...
    ```
* In some cases the steps of your pipeline will have conflicting requirements or some steps of your pipeline will require large dependencies that don't need to be installed to run the remaining steps of your pipeline. For this case, ZenML allows you to specify custom Docker settings for steps in your pipeline.

```python
docker_settings = DockerSettings(requirements=["tensorflow"])


@step(settings={"docker": docker_settings})
def my_training_step(...):
    ...
```

{% hint style="info" %}
You can combine these methods but do make sure that your list of requirements does not overlap with the ones specified explicitly in the Docker settings.
{% endhint %}

Depending on the options specified in your Docker settings, ZenML installs the requirements in the following order (each step optional):

* The packages installed in your local python environment
* The packages required by the stack unless this is disabled by setting `install_stack_requirements=False`.
* The packages specified via the `required_integrations`
* The packages specified via the `requirements` attribute
* You can specify additional arguments for the installer used to install your Python packages as follows:
```python
# This will result in a `pip install --timeout=1000 ...` call when installing packages in the
# Docker image
docker_settings = DockerSettings(python_package_installer_args={"timeout": 1000})

@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```
* **Experimental**: If you want to use [`uv`](https://github.com/astral-sh/uv) for faster resolving and installation of your Python packages, you can use by it as follows:

```python
docker_settings = DockerSettings(python_package_installer="uv")

@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

{% hint style="info" %}
`uv` is a relatively new project and not as stable as `pip` yet, which might lead to errors during package installation. If this happens, try switching the installer back to `pip` and see if that solves the issue.
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
