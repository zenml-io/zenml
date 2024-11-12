---
description: Sharing code and libraries within teams.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Shared Libraries and Logic for Teams

Teams often need to collaborate on projects, share versioned logic, and implement cross-cutting functionality that benefits the entire organization. Sharing code libraries allows for incremental improvements, increased robustness, and standardization across projects.

This guide will cover two main aspects of sharing code within teams using ZenML:

1. What can be shared
2. How to distribute shared components

## What Can Be Shared

ZenML offers several types of custom components that can be shared between teams:

### Custom Flavors

Custom flavors are special integrations that don't come built-in with ZenML. These can be implemented and shared as follows:

1. Create the custom flavor in a shared repository.
2. Implement the custom stack component as described in the [ZenML documentation](../stack-deployment/implement-a-custom-stack-component.md#implementing-a-custom-stack-component-flavor).
3. Register the component using the ZenML CLI, for example in the case of a custom artifact store flavor:

```bash
zenml artifact-store flavor register <path.to.MyS3ArtifactStoreFlavor>
```

### Custom Steps

Custom steps can be created and shared via a separate repository. Team members can reference these components as they would normally reference Python modules.

### Custom Materializers

Custom materializers are common components that teams often need to share. To implement and share a custom materializer:

1. Create the materializer in a shared repository.
2. Implement the custom materializer as described in the [ZenML documentation](https://docs.zenml.io/how-to/handle-data-artifacts/handle-custom-data-types).
3. Team members can import and use the shared materializer in their projects.

## How to Distribute Shared Components

There are several methods to distribute and use shared components within a team:

### Shared Private Wheels

Using shared private wheels is an effective approach to sharing code within a team. This method packages Python code for internal distribution without making it publicly available.

#### Benefits of Using Shared Private Wheels

- Packaged format: Easy to install using pip
- Version management: Simplifies managing different code versions
- Dependency management: Automatically installs specified dependencies
- Privacy: Can be hosted on internal PyPI servers
- Smooth integration: Imported like any other Python package

#### Setting Up Shared Private Wheels

1. Create a private PyPI server or use a service like [AWS CodeArtifact](https://aws.amazon.com/codeartifact/).
2. [Build your code](https://packaging.python.org/en/latest/tutorials/packaging-projects/) [into wheel format](https://opensource.com/article/23/1/packaging-python-modules-wheels).
3. Upload the wheel to your private PyPI server.
4. Configure pip to use the private PyPI server in addition to the public one.
5. Install the private packages using pip, just like public packages.

### Using Shared Libraries with `DockerSettings`

When running pipelines with remote orchestrators, ZenML generates a `Dockerfile` at runtime. You can use the `DockerSettings` class to specify how to include your shared libraries in this Docker image.

#### Installing Shared Libraries

Here are some ways to include shared libraries using `DockerSettings`. Either specify a list of requirements:

```python
import os
from zenml.config import DockerSettings
from zenml import pipeline

docker_settings = DockerSettings(
    requirements=["my-simple-package==0.1.0"],
    environment={'PIP_EXTRA_INDEX_URL': f"https://{os.environ.get('PYPI_TOKEN', '')}@my-private-pypi-server.com/{os.environ.get('PYPI_USERNAME', '')}/"}
)

@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

Or you can also use a requirements file:

```python
docker_settings = DockerSettings(requirements="/path/to/requirements.txt")

@pipeline(settings={"docker": docker_settings})
def my_pipeline(...):
    ...
```

The `requirements.txt` file would specify the private index URL in the following
way, for example:

```
--extra-index-url https://YOURTOKEN@my-private-pypi-server.com/YOURUSERNAME/
my-simple-package==0.1.0
```

For information on using private PyPI repositories to share your code, see our [documentation on how to use a private PyPI repository](../customize-docker-builds/how-to-use-a-private-pypi-repository.md).

## Best Practices

Regardless of what you're sharing or how you're distributing it, consider these best practices:

- Use version control for shared code repositories.

Version control systems like Git allow teams to collaborate on code effectively. They provide a central repository where all team members can access the latest version of the shared components and libraries.

- Implement proper access controls for private PyPI servers or shared repositories.

To ensure the security of proprietary code and libraries, it's crucial to set up appropriate access controls. This may involve using authentication mechanisms, managing user permissions, and regularly auditing access logs.

- Maintain clear documentation for shared components and libraries.

Comprehensive and up-to-date documentation is essential for the smooth usage and maintenance of shared code. It should cover installation instructions, API references, usage examples, and any specific guidelines or best practices.

- Regularly update shared libraries and communicate changes to the team.

As the project evolves, it's important to keep shared libraries updated with the latest bug fixes, performance improvements, and feature enhancements. Establish a process for regularly updating and communicating these changes to the team.

- Consider setting up continuous integration for shared libraries to ensure quality and compatibility.

Continuous integration (CI) helps maintain the stability and reliability of shared components. By automatically running tests and checks on each code change, CI can catch potential issues early and ensure compatibility across different environments and dependencies.

By leveraging these methods for sharing code and libraries, teams can
collaborate more effectively, maintain consistency across projects, and
accelerate development processes within the ZenML framework.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
