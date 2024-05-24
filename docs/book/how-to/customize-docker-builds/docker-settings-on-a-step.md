---
description: You have the option to customize the docker settings at a step level.
---

# Docker settings on a step

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
<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


