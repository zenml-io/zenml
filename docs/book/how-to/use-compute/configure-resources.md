---
description: >-
  Some orchestrators allow you to specify resources like memory, cpu and gpu
  core count.
---

# Configure resources

```python
from zenml import step
from zenml.config import ResourceSettings, DockerSettings

@step(
  settings={
    "resources": ResourceSettings(
      memory="16GB", gpu_count="1", cpu_count="8"
    ),
  }
)
def training(...):
	...
```
