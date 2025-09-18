---
description: >-
  Customize Docker builds to run your pipelines in isolated, well-defined
  environments.
icon: docker
---

# Containerization

ZenML executes pipeline steps sequentially in the active Python environment when running locally. However, with remote [orchestrators](https://docs.zenml.io/stacks/orchestrators) or [step operators](https://docs.zenml.io/stacks/step-operators), ZenML builds [Docker](https://www.docker.com/) images to run your pipeline in an isolated, well-defined environment.

This page explains how ZenML's Docker build process works and how you can customize it to meet your specific requirements.

## Understanding Docker Builds in ZenML

When a pipeline is run with a remote orchestrator, a Dockerfile is dynamically generated at runtime. It is then used to build the Docker image using the image builder component of your stack. The Dockerfile consists of the following steps:

1. **Starts from a parent image** that has ZenML installed. By default, this will use the [official ZenML image](https://hub.docker.com/r/zenmldocker/zenml/) for the Python and ZenML version that you're using in the active Python environment.
2. **Installs additional pip dependencies**. ZenML automatically detects which integrations are used in your stack and installs the required dependencies.
3. **Optionally copies your source files**. Your source files need to be available inside the Docker container so ZenML can execute your step code.
4. **Sets user-defined environment variables.**

The process described above is automated by ZenML and covers most basic use cases. This page covers various ways to customize the Docker build process to fit your specific needs.

### Docker Build Process

ZenML uses the following process to decide how to build Docker images:

* **No `dockerfile` specified**: If any of the options regarding requirements, environment variables, or copying files require us to build an image, ZenML will build this image. Otherwise, the `parent_image` will be used to run the pipeline.
* **`dockerfile` specified**: ZenML will first build an image based on the specified Dockerfile. If any additional options regarding requirements, environment variables, or copying files require an image built on top of that, ZenML will build a second image. If not, the image built from the specified Dockerfile will be used to run the pipeline.

### Requirements Installation Order

Depending on the configuration of your Docker settings, requirements will be installed in the following order (each step is optional):

1. The packages installed in your local Python environment (if enabled)
2. The packages required by the stack (unless disabled by setting `install_stack_requirements=False`)
3. The packages specified via the `required_integrations` 
4. The packages specified via the `requirements` attribute

For a full list of configuration options, check out [the DockerSettings object on the SDKDocs](https://sdkdocs.zenml.io/latest/core_code_docs/core-config.html#zenml.config.DockerSettings).

## Configuring Docker Settings

You can customize Docker builds for your pipelines and steps using the `DockerSettings` class:

```python
from zenml.config import DockerSettings
```

There are multiple ways to supply these settings:

### Pipeline-Level Settings

Configuring settings on a pipeline applies them to all steps of that pipeline:

```python
from zenml import pipeline, step
from zenml.config import DockerSettings

docker_settings = DockerSettings()

@step
def my_step() -> None:
    """Example step."""
    pass

# Either add it to the decorator
@pipeline(settings={"docker": docker_settings})
def my_pipeline() -> None:
    my_step()

# Or configure the pipelines options
my_pipeline = my_pipeline.with_options(
    settings={"docker": docker_settings}
)
```

### Step-Level Settings

For more fine-grained control, configure settings on individual steps. This is particularly useful when different steps have conflicting requirements or when some steps need specialized environments:

```python
from zenml import step
from zenml.config import DockerSettings

docker_settings = DockerSettings()

# Either add it to the decorator
@step(settings={"docker": docker_settings})
def my_step() -> None:
    pass

# Or configure the step options
my_step = my_step.with_options(
    settings={"docker": docker_settings}
)
```

### Using YAML Configuration

Define settings in a YAML configuration file for better separation of code and configuration:

```yaml
settings:
    docker:
        parent_image: python:3.9-slim
        apt_packages:
          - git
          - curl
        requirements:
          - tensorflow==2.8.0
          - pandas

steps:
  training_step:
    settings:
        docker:
            parent_image: pytorch/pytorch:2.2.0-cuda11.8-cudnn8-runtime
            required_integrations:
              - wandb
              - mlflow
```

Check out [this page](https://docs.zenml.io/concepts/steps_and_pipelines/configuration) for more information on the hierarchy and precedence of the various ways in which you can supply the settings.

### Specifying Docker Build Options

You can customize the build process by specifying build options that get passed to the build method of the image builder:

```python
from zenml import pipeline
from zenml.config import DockerSettings

docker_settings = DockerSettings(
    build_config={"build_options": {"buildargs": {"MY_ARG": "value"}}}
)

@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

For the default local image builder, these options are passed to the [`docker build` command](https://docker-py.readthedocs.io/en/stable/images.html#docker.models.images.ImageCollection.build).

{% hint style="info" %}
If you're running your pipelines on MacOS with ARM architecture, the local Docker caching does not work unless you specify the target platform of the image:

```python
from zenml import pipeline
from zenml.config import DockerSettings

docker_settings = DockerSettings(
    build_config={"build_options": {"platform": "linux/amd64"}}
)

@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```
{% endhint %}

## Using Custom Parent Images

### Pre-built Parent Images

To use a static parent image (e.g., with internal dependencies pre-installed):

```python
from zenml import pipeline
from zenml.config import DockerSettings

docker_settings = DockerSettings(parent_image="my_registry.io/image_name:tag")

@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

ZenML will use this image as the base and still perform the following steps:

1. Install additional pip dependencies
2. Copy source files (if configured)
3. Set environment variables

{% hint style="info" %}
If you're going to use a custom parent image, you need to make sure that it has Python, pip, and ZenML installed for it to work. If you need a starting point, you can take a look at the Dockerfile that ZenML uses [here](https://github.com/zenml-io/zenml/blob/main/docker/base.Dockerfile).
{% endhint %}

### Skip Build Process

To use the image directly to run your steps without including any code or installing any requirements on top of it, skip the Docker builds by setting `skip_build=True`:

```python
docker_settings = DockerSettings(
    parent_image="my_registry.io/image_name:tag",
    skip_build=True
)

@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

When `skip_build` is enabled, the `parent_image` will be used directly to run the steps of your pipeline without any additional Docker builds on top of it. This means that **none** of the following will happen:

- No installation of local Python environment packages
- No installation of stack requirements
- No installation of required integrations
- No installation of specified requirements
- No installation of apt packages
- No inclusion of source files in the container
- No setting of environment variables

{% hint style="warning" %}
This is an advanced feature and may cause unintended behavior when running your pipelines. If you use this, ensure your image contains everything necessary to run your pipeline:

1. Your stack requirements
2. Integration requirements
3. Project-specific requirements
4. Any system packages
5. Your project code files (unless a code repository is registered or `allow_download_from_artifact_store` is enabled)

Make sure that Python, `pip` and `zenml` are installed in your image, and that your code is in the `/app` directory set as the active working directory.

Also note that the Docker settings validator will raise an error if you set `skip_build=True` without specifying a `parent_image`. A parent image is required when skipping the build as it will be used directly to run your pipeline steps.
{% endhint %}

### Custom Dockerfiles

For greater control, you can specify a custom Dockerfile and build context:

```python
docker_settings = DockerSettings(
    dockerfile="/path/to/dockerfile",
    build_context_root="/path/to/build/context",
    parent_image_build_config={
        "build_options": {"buildargs": {"MY_ARG": "value"}},
        "dockerignore": "/path/to/.dockerignore"
    }
)

@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

Here is how the build process looks like with a custom Dockerfile:

* **`Dockerfile` specified**: ZenML will first build an image based on the specified `Dockerfile`. If any options regarding requirements, environment variables, or copying files require an additional image built on top of that, ZenML will build a second image. Otherwise, the image built from the specified `Dockerfile` will be used to run the pipeline.

{% hint style="info" %}
Important notes about using a custom Dockerfile:

* When you specify a custom `dockerfile`, the `parent_image` attribute will be ignored
* The image built from your Dockerfile must have ZenML installed
* If you set `build_context_root`, that directory will be used as the build context for the Docker build. If left empty, the build context will only contain the Dockerfile
* You can configure the build options by setting `parent_image_build_config` with specific build options and dockerignore settings
{% endhint %}

## Managing Dependencies

ZenML offers several ways to specify dependencies for your Docker containers:

### Python Dependencies

By default, ZenML automatically installs all packages required by your active ZenML stack. 

{% hint style="warning" %}
In future versions, if none of the `replicate_local_python_environment`, `pyproject_path` or `requirements` attributes on `DockerSettings` are specified, ZenML will try to automatically find a `requirements.txt` and `pyproject.toml` files inside your current source root and install packages from the first one it finds. You can disable this behavior by setting `disable_automatic_requirements_detection=True`. If
you already want this automatic detection in current versions of ZenML, set `disable_automatic_requirements_detection=False`.
{% endhint %}

1.  **Replicate Local Environment**:
    ```python
    from zenml import pipeline
    from zenml.config import DockerSettings
    
    docker_settings = DockerSettings(replicate_local_python_environment=True)


    @pipeline(settings={"docker": docker_settings})
    def my_pipeline(...):
        ...
    ```

    This will run `pip freeze` to get a list of the installed packages in your local Python environment and will install them in the Docker image. This ensures that the same
    exact dependencies will be installed.
    {% hint style="warning" %}
    This does not work when you have a local project installed. To install local projects, check out the `Install Local Projects` section below.
    {% endhint %}
2.  **Specify a `pyproject.toml` file**:

    ```python
    from zenml import pipeline
    from zenml.config import DockerSettings
    
    docker_settings = DockerSettings(pyproject_path="/path/to/pyproject.toml")

    @pipeline(settings={"docker": docker_settings})
    def my_pipeline(...):
        ...
    ```

    By default, ZenML will try to export the dependencies specified in the `pyproject.toml` by trying to run `uv export` and `poetry export`.
    If both of these commands do not work for your `pyproject.toml` file or you want to customize the command (for example to install certain
    extras), you can specify a custom command using the `pyproject_export_command` attribute. This command must output a list of requirements following the format of the [requirements file](https://pip.pypa.io/en/stable/reference/requirements-file-format/). The command can contain a `{directory}` placeholder which will be replaced with the directory in which the `pyproject.toml` file is stored.

    ```python
    from zenml import pipeline
    from zenml.config import DockerSettings

    docker_settings = DockerSettings(pyproject_export_command=[
        "uv",
        "export",
        "--extra=train",
        "--format=requirements-txt"
        "--directory={directory}
    ])


    @pipeline(settings={"docker": docker_settings})
    def my_pipeline(...):
        ...
    ```
3.  **Specify Requirements Directly**:

    ```python
    from zenml.config import DockerSettings
    
    docker_settings = DockerSettings(requirements=["torch==1.12.0", "torchvision"])
    ```
4.  **Use Requirements File**:

    ```python
    from zenml.config import DockerSettings
    
    docker_settings = DockerSettings(requirements="/path/to/requirements.txt")
    ```
5.  **Specify ZenML Integrations**:

    ```python
    from zenml.integrations.constants import PYTORCH, EVIDENTLY
    from zenml.config import DockerSettings

    docker_settings = DockerSettings(required_integrations=[PYTORCH, EVIDENTLY])
    ```
6.  **Control Stack Requirements**:
    By default, ZenML installs the requirements needed by your active stack. You can disable this behavior if needed:

    ```python
    from zenml.config import DockerSettings
    
    docker_settings = DockerSettings(install_stack_requirements=False)
    ```

7.  **Install Local Projects**:
    If your code requires the installation of some local code files as a python package, you can specify a command
    that installs it as follows:
    ```python
    from zenml.config import DockerSettings
    
    docker_settings = DockerSettings(local_project_install_command="pip install . --no-deps")
    ```

    {% hint style="warning" %}
    Installing a local python package only works if your code files are included in the Docker image, so make sure you have
    `allow_including_files_in_images=True` in your Docker settings. If you want to instead use the [code download functionality](#source-code-management)
    to avoid building new Docker images for each pipeline run, you can follow [this example](https://github.com/zenml-io/zenml-patterns/tree/main/docker-local-pkg). 
    {% endhint %}

Depending on the options specified in your Docker settings, ZenML installs the requirements in the following order (each step optional):

1. The packages installed in your local Python environment
2. The packages required by the stack (unless disabled by setting `install_stack_requirements=False`)
3. The packages specified via the `required_integrations`
4. The packages defined in the pyproject.toml file specified by the `pyproject_path` attribute
5. The packages specified via the `requirements` attribute

### System Packages

Specify apt packages to be installed in the Docker image:

```python
from zenml.config import DockerSettings

docker_settings = DockerSettings(apt_packages=["git", "curl", "libsm6", "libxext6"])
```

### Installation Control

Control how packages are installed:

```python
# Use custom installer arguments
docker_settings = DockerSettings(python_package_installer_args={"timeout": 1000})

# Use pip instead of uv
from zenml.config import DockerSettings, PythonPackageInstaller
docker_settings = DockerSettings(python_package_installer=PythonPackageInstaller.PIP)
# Or as a string
docker_settings = DockerSettings(python_package_installer="pip")

# Use uv (default)
docker_settings = DockerSettings(python_package_installer=PythonPackageInstaller.UV)
```

The available package installers are:
- `uv`: The default python package installer
- `pip`: An alternative python package installer

Full documentation for how `uv` works with PyTorch can be found on the Astral Docs website [here](https://docs.astral.sh/uv/guides/integration/pytorch/). It covers some of the particular gotchas and details you might need to know.

## Private PyPI Repositories

For packages that require authentication from private repositories:

```python
import os

docker_settings = DockerSettings(
    requirements=["my-internal-package==0.1.0"],
    environment={
        'PIP_EXTRA_INDEX_URL': f"https://{os.environ.get('PYPI_TOKEN', '')}@my-private-pypi-server.com/{os.environ.get('PYPI_USERNAME', '')}/"}
)
```

Be cautious with handling credentials. Always use secure methods to manage and distribute authentication information within your team. Consider using secrets management tools or environment variables passed securely.

## Source Code Management

ZenML determines the root directory of your source files in the following order:

1. If you've initialized zenml (`zenml init`) in your current working directory or one of its parent directories, the repository root directory will be used.
2. Otherwise, the parent directory of the Python file you're executing will be the source root. For example, running `python /path/to/file.py`, the source root would be `/path/to`.

You can specify how the files inside this root directory are handled:

```python
docker_settings = DockerSettings(
    # Download files from code repository if available
    allow_download_from_code_repository=True,
    # If no code repository, upload code to artifact store
    allow_download_from_artifact_store=True,
    # If neither of the above, include files in the image
    allow_including_files_in_images=True
)
```

ZenML handles your source code in the following order:

1. If `allow_download_from_code_repository` is `True` and your files are inside a registered [code repository](https://docs.zenml.io/user-guides/production-guide/connect-code-repository) and the repository has no local changes, the files will be downloaded from the code repository and not included in the image.
2. If the previous option is disabled or no code repository without local changes exists for the root directory, ZenML will archive and upload your code to the artifact store if `allow_download_from_artifact_store` is `True`.
3. If both previous options were disabled or not possible, ZenML will include your files in the Docker image if `allow_including_files_in_images` is enabled. This means a new Docker image has to be built each time you modify one of your code files.

{% hint style="warning" %}
Setting all of the above attributes to `False` is not recommended and will most likely cause unintended and unanticipated behavior when running your pipelines. If you do this, you're responsible that all your files are at the correct paths in the Docker images that will be used to run your pipeline steps.
{% endhint %}

### Controlling Included Files

* When downloading files from a code repository, use a `.gitignore` file to exclude files.
*   When including files in the image, use a `.dockerignore` file to exclude files and keep the image smaller:

    ```python
    # Have a file called .dockerignore in your source root directory
    # Or explicitly specify a .dockerignore file to use:
    docker_settings = DockerSettings(build_config={"dockerignore": "/path/to/.dockerignore"})
    ```

## Environment Variables

You can configure environment variables that will be set in the beginning of the Docker image building process before any python or apt packages are installed:

```python
docker_settings = DockerSettings(
    environment={
        "PYTHONUNBUFFERED": "1",
        "MODEL_DIR": "/models",
        "API_KEY": "${GLOBAL_API_KEY}"  # Reference a local environment variable
    }
)
```

Environment variables can reference other environment variables set in your client environment by using the `${VAR_NAME}` syntax. ZenML will substitute these before building the images.

## Build Reuse and Optimization

ZenML automatically reuses Docker builds when possible to save time and resources:

### What is a Pipeline Build?

A pipeline build is an encapsulation of a pipeline and the stack it was run on. It contains the Docker images that were built for the pipeline with all required dependencies from the stack, integrations and the user. Optionally, it also contains the pipeline code.

List all available builds for a pipeline:

```bash
zenml pipeline builds list --pipeline_id='startswith:ab53ca'
```

Create a build manually (useful for pre-building images):

```bash
zenml pipeline build --stack vertex-stack my_module.my_pipeline_instance
```

You can use options to specify the configuration file and the stack to use for the build. Learn more about the build function [here](https://sdkdocs.zenml.io/latest/cli.html#zenml.cli.Pipeline.build).

### Reusing Builds

By default, when you run a pipeline, ZenML will check if a build with the same pipeline and stack exists. If it does, it will reuse that build automatically. However, you can also force using a specific build by providing its ID:

```python
pipeline_instance.run(build="<build_id>")
```

You can also specify this in configuration files:

```yaml
build: your-build-id-here
```

{% hint style="warning" %}
Specifying a custom build when running a pipeline will **not run the code on your client machine** but will use the code **included in the Docker images of the build**. Even if you make local code changes, reusing a build will _always_ execute the code bundled in the Docker image, rather than the local code.
{% endhint %}

### Controlling Image Repository Names

You can control where your Docker image is pushed by specifying a target repository name:

```python
from zenml.config import DockerSettings

docker_settings = DockerSettings(target_repository="my-custom-repo-name")
```

The repository name will be appended to the registry URI of your container registry stack component. For example, if your container registry URI is `gcr.io/my-project` and you set `target_repository="zenml-pipelines"`, the full image name would be `gcr.io/my-project/zenml-pipelines`.

If you don't specify a target repository, the default repository name configured in your container registry stack component settings will be used.

### Decoupling Code from Builds

To reuse Docker builds while still using your latest code changes, you need to decouple your code from the build. There are two main approaches:

#### 1. Using the Artifact Store to Upload Code

You can let ZenML use the artifact store to upload your code. This is the default behavior if no code repository is detected and the `allow_download_from_artifact_store` flag is not set to `False` in your `DockerSettings`.

#### 2. Using Code Repositories for Faster Builds

Registering a [code repository](../code-repositories/code-repositories.md) lets you avoid building images each time you run a pipeline **and** quickly iterate on your code. When running a pipeline that is part of a local code repository checkout, ZenML can instead build the Docker images without including any of your source files, and download the files inside the container before running your code.

ZenML will **automatically figure out which builds match your pipeline and reuse the appropriate build id**. Therefore, you **do not** need to explicitly pass in the build id when you have a clean repository state and a connected git repository.

{% hint style="warning" %}
In order to benefit from the advantages of having a code repository in a project, you need to make sure that **the relevant integrations are installed for your ZenML installation.**. For instance, let's assume you are working on a project with ZenML and one of your team members has already registered a corresponding code repository of type `github` for it. If you do `zenml code-repository list`, you would also be able to see this repository. However, in order to fully use this repository, you still need to install the corresponding integration for it, in this example the `github` integration.

```sh
zenml integration install github
```
{% endhint %}

#### Detecting local code repository checkouts

Once you have registered one or more code repositories, ZenML will check whether the files you use when running a pipeline are tracked inside one of those code repositories. This happens as follows:

* First, the source root is computed
* Next, ZenML checks whether this source root directory is included in a local checkout of one of the registered code repositories

#### Tracking code versions for pipeline runs

If a local code repository checkout is detected when running a pipeline, ZenML will store a reference to the current commit for the pipeline run, so you'll be able to know exactly which code was used.

Note that this reference is only tracked if your local checkout is clean (i.e. it does not contain any untracked or uncommitted files). This is to ensure that your pipeline is actually running with the exact code stored at the specific code repository commit.

{% hint style="info" %}
If you want to ignore untracked files, you can set the `ZENML_CODE_REPOSITORY_IGNORE_UNTRACKED_FILES` environment variable to `True`. When doing this, you're responsible that the files committed to the repository includes everything necessary to run your pipeline.
{% endhint %}

#### Preventing Build Reuse
 
 There might be cases where you want to force a new build, even if a suitable existing build is available. You can do this by setting `prevent_build_reuse=True`:
 
 ```python
 docker_settings = DockerSettings(prevent_build_reuse=True)
 ```
 
 This is useful in scenarios like:
 - When you've made changes to your image building process that aren't tracked by ZenML
 - When troubleshooting issues in your Docker image
 - When you want to ensure your Docker image uses the most up-to-date base images

#### Tips and Best Practices for Build Reuse

* **Clean Repository State**: The file download is only possible if the local checkout is clean (no untracked or uncommitted files) and the latest commit has been pushed to the remote repository.
* **Configuration Options**: If you want to disable or enforce downloading of files, check the [DockerSettings](https://sdkdocs.zenml.io/latest/index.html#zenml.config.DockerSettings) for available options.
* **Team Collaboration**: Using code repositories allows team members to reuse images that colleagues might have built for the same stack, enhancing collaboration efficiency.
* **Build Selection**: ZenML automatically selects matching builds, but you can override this with explicit build IDs for special cases.

## Image Build Location

By default, execution environments are created locally using the local Docker client. However, this requires Docker installation and permissions. ZenML offers [image builders](https://docs.zenml.io/stacks/image-builders), a special [stack component](https://docs.zenml.io/stacks), allowing users to build and push Docker images in a different specialized _image builder environment_.

Note that even if you don't configure an image builder in your stack, ZenML still uses the [local image builder](https://docs.zenml.io/stacks/image-builders/local) to retain consistency across all builds. In this case, the image builder environment is the same as the [client environment](https://docs.zenml.io/user-guides/best-practices/configure-python-environments#client-environment-or-the-runner-environment).

You don't need to directly interact with any image builder in your code. As long as the image builder that you want to use is part of your active [ZenML stack](https://docs.zenml.io/user-guides/production-guide/understand-stacks), it will be used automatically by any component that needs to build container images.

## Container User Permissions

By default, Docker containers often run as the `root` user, which can pose security risks. ZenML allows you to specify a different user to run your containers:

```python
docker_settings = DockerSettings(user="non-root-user")
```

When you set the `user` parameter:
- The specified user will become the owner of the `/app` directory, which contains all your code
- The container entrypoint will run as this user instead of root
- This can help improve security by following the principle of least privilege

## Best Practices

1. **Use code repositories** to speed up builds and enable team collaboration. This approach is highly recommended for production environments.
2. **Keep dependencies minimal** to reduce build times. Only include packages you actually need.
3. **Use fine-grained Docker settings** at the step level for conflicting requirements. This prevents dependency conflicts and reduces image sizes.
4. **Use pre-built images** for common environments. This can significantly speed up your workflow.
5. **Configure dockerignore files** to reduce image size. Large Docker images take longer to build, push, and pull.
6. **Leverage build caching** by structuring your Dockerfiles and build processes to maximize cache hits.
7. **Use environment variables** for configuration instead of hardcoding values in your images.
8. **Test your Docker builds locally** before using them in production pipelines.
9. **Keep your repository clean** (no uncommitted changes) when running pipelines to ensure ZenML can correctly track code versions.
10. **Use metadata and labels** to help identify and manage your Docker images.
11. **Run containers as non-root users** when possible to improve security.

By following these practices, you can optimize your Docker builds in ZenML and create a more efficient workflow.
