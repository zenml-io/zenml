---
description: You have the option to customize the Docker settings at a step level.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Docker settings on a step

By default every step of a pipeline uses the same Docker image that is defined at the [pipeline level](./docker-settings-on-a-pipeline.md). Sometimes your steps will have special requirements that make it necessary to define a different Docker image for one or many steps. This can easily be accomplished by adding the [DockerSettings](https://sdkdocs.zenml.io/latest/core_code_docs/core-config/#zenml.config.docker_settings.DockerSettings) to the step decorator directly.

```python
from zenml import step
from zenml.config import DockerSettings

@step(
  settings={
    "docker": DockerSettings(
      parent_image="pytorch/pytorch:1.12.1-cuda11.3-cudnn8-runtime"
    )
  }
)
def training(...):
	...
```

Alternatively, this can also be done within the configuration file.

```yaml
steps:
  training:
    settings:
      docker:
        parent_image: pytorch/pytorch:2.2.0-cuda11.8-cudnn8-runtime
        required_integrations:
          - gcp
          - github
        requirements:
          - zenml  # Make sure to include ZenML for other parent images
          - numpy
```
<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


