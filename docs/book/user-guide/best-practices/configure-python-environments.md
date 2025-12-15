---
icon: python
description: Navigating multiple development environments.
---

# Configure python environments

ZenML deployments often involve multiple environments. This guide helps you manage dependencies and configurations across these environments.

Here is a visual overview of the different environments:

<figure><img src="../../.gitbook/assets/SystemArchitecture.png" alt=""><figcaption><p>Left box is the client environment, middle is the zenml server environment, and the right most contains the build environments</p></figcaption></figure>

## Client Environment (or the Runner environment)

The client environment (sometimes known as the runner environment) is where the ZenML pipelines are _compiled_, i.e., where you call the pipeline function (typically in a `run.py` script). There are different types of client environments:

* A local development environment
* A CI runner in production.
* A [ZenML Pro](https://zenml.io/pro) runner.
* A `runner` image orchestrated by the ZenML server to start pipelines.

In all the environments, you should use your preferred package manager (e.g., `pip` or `poetry`) to manage dependencies. Ensure you install the ZenML package and any required [integrations](https://docs.zenml.io/stacks).

The client environment typically follows these key steps when starting a pipeline:

1. Compiling an intermediate pipeline representation via the `@pipeline` function.
2. Creating or triggering [pipeline and step build environments](https://docs.zenml.io/stacks/image-builders) if running remotely.
3. Triggering a run in the [orchestrator](https://docs.zenml.io/stacks/orchestrators).

Please note that the `@pipeline` function in your code is **only ever called** in this environment. Therefore, any computational logic that is executed in the pipeline function needs to be relevant to this so-called _compile time_, rather than at _execution_ time, which happens later.

## ZenML Server Environment

The ZenML server environment is a FastAPI application managing pipelines and metadata. It includes the ZenML UI and is accessed when you [deploy ZenML](https://docs.zenml.io/deploying-zenml/deploying-zenml). To manage dependencies, install them during [ZenML deployment](https://docs.zenml.io/deploying-zenml/deploying-zenml), but only if you have custom integrations, as most are built-in.

## Execution Environments

When running locally, there is no real concept of an `execution` environment as the client, server, and execution environment are all the same. However, when running a pipeline remotely, ZenML needs to transfer your code and environment over to the remote [orchestrator](https://docs.zenml.io/stacks/orchestrators). In order to achieve this, ZenML builds Docker images known as `execution environments`.

ZenML handles the Docker image configuration, creation, and pushing, starting with a [base image](https://hub.docker.com/r/zenmldocker/zenml) containing ZenML and Python, then adding pipeline dependencies. To manage the Docker image configuration, follow the steps in the [containerize your pipeline](https://docs.zenml.io/concepts/containerization) guide, including specifying additional pip dependencies, using a custom parent image, and customizing the build process.

## Image Builder Environment

By default, execution environments are created locally in the [client environment](#client-environment-or-the-runner-environment) using the local Docker client. However, this requires Docker installation and permissions. ZenML offers [image builders](https://docs.zenml.io/stacks/image-builders), a special [stack component](https://docs.zenml.io/stacks), allowing users to build and push Docker images in a different specialized _image builder environment_.

Note that even if you don't configure an image builder in your stack, ZenML still uses the [local image builder](https://docs.zenml.io/stacks/image-builders/local) to retain consistency across all builds. In this case, the image builder environment is the same as the client environment.

## Handling dependencies

When using ZenML with other libraries, you may encounter issues with conflicting dependencies. ZenML aims to be stack- and integration-agnostic, allowing you to run your pipelines using the tools that make sense for your problems. With this flexibility comes the possibility of dependency conflicts.

ZenML allows you to install dependencies required by integrations through the `zenml integration install ...` command. This is a convenient way to install dependencies for a specific integration, but it can also lead to dependency conflicts if you are using other libraries in your environment. An easy way to see if the ZenML requirements are still met (after installing any extra dependencies required by your work) by running `zenml integration list` and checking that your desired integrations still bear the green tick symbol denoting that all requirements are met.

## Suggestions for Resolving Dependency Conflicts

### Use a tool like `pip-compile` for reproducibility

Consider using a tool like `pip-compile` (available through [the `pip-tools`
package](https://pip-tools.readthedocs.io/)) to compile your dependencies into a
static `requirements.txt` file that can be used across environments. (If you are
using [`uv`](https://github.com/astral-sh/uv), you might want to use `uv pip compile` as an alternative.)

For a practical example and explanation of using `pip-compile` to address exactly this need, see [our 'gitflow' repository and workflow](https://github.com/zenml-io/zenml-gitflow#-software-requirements-management) to learn more.

### Use `pip check` to discover dependency conflicts

Running [`pip check`](https://pip.pypa.io/en/stable/cli/pip\_check/) will verify that your environment's dependencies are compatible with one another. If not, you will see a list of the conflicts. This may or may not be a problem or something that will prevent you from moving forward with your specific use case, but it is certainly worth being aware of whether this is the case.

### Well-known dependency resolution issues

Some of ZenML's integrations come with strict dependency and package version
requirements. We try to keep these dependency requirements ranges as wide as
possible for the integrations developed by ZenML, but it is not always possible
to make this work completely smoothly. Here is one of the known issues:

* `click`: ZenML currently requires `click~=8.0.3` for its CLI. This is on account of another dependency of ZenML. Using versions of `click` in your own project that are greater than 8.0.3 may cause unanticipated behaviors.

### Manually bypassing ZenML's integration installation

It is possible to skip ZenML's integration installation process and install dependencies manually. This is not recommended, but it is possible and can be run at your own risk.

{% hint style="info" %}
Note that the `zenml integration install ...` command runs a `pip install ...` under the hood as part of its implementation, taking the dependencies listed in the integration object and installing them. For example, `zenml integration install gcp` will run `pip install "kfp==1.8.16" "gcsfs" "google-cloud-secret-manager" ...` and so on, since they are [specified in the integration definition](https://github.com/zenml-io/zenml/blob/main/src/zenml/integrations/gcp/__init__.py#L46).
{% endhint %}

To do this, you will need to install the dependencies for the integration you
want to use manually. You can find the dependencies for the integrations by
running the following:

```bash
# to have the requirements exported to a file
zenml integration export-requirements --output-file integration-requirements.txt INTEGRATION_NAME

# to have the requirements printed to the console
zenml integration export-requirements INTEGRATION_NAME
```

You can then amend and tweak those requirements as you see fit. Note that if you are using a remote orchestrator, you would then have to place the updated versions for the dependencies in a `DockerSettings` object (described in detail [here](https://docs.zenml.io/concepts/containerization#pipeline-level-settings)) which will then make sure everything is working as you need.