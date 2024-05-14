---
description: >-
  ZenML allows you to fully customize the docker images that are used for code
  execution.
---

# 🐳 Handle requirements and Docker settings

```python
docker_settings = DockerSettings(
    requirements=["tensorflow"],
    dockerignore="/path/to/.dockerignore")
    apt_packages=["git"]
)


@step(settings={"docker": docker_settings})
def my_training_step(...):
    ...
```

{% hint style="info" %}
Find an extensive list of settings including explanations [here](../../user-guide/advanced-guide/infrastructure-management/containerize-your-pipeline.md).
{% endhint %}
