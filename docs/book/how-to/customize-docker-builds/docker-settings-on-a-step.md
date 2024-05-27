---
description: You have the option to customize the docker settings at a step level.
---

# Docker settings on a step

By default every step of a pipeline uses the same docker image that is defined at the pipeline level. Sometimes your steps will have special requirements that make it necessary to define a different docker image for one or many steps. This can easily be accomplished by adding the docker settings to the step decorator directly.&#x20;

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
