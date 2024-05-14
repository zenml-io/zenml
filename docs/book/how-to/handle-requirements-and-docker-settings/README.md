---
description: >-
  ZenML allows you to fully customize the docker images that are used for code
  execution.
---

# 🐳 Handle requirements and Docker settings

```python
from zenml import pipeline
from zenml.config import DockerSettings

docker_settings = DockerSettings(
    requirements=["tensorflow"],
    dockerignore="/path/to/.dockerignore")
    apt_packages=["git"]
)


@pipeline(settings={"docker": docker_settings})
def my_training_step(...):
    ...
```

{% hint style="info" %}
Find an extensive list of docker settings including full explanations [here](../../user-guide/advanced-guide/infrastructure-management/containerize-your-pipeline.md).
{% endhint %}
