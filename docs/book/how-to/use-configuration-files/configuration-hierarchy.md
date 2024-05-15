---
description: >-
  When things can be configured on the pipeline and step level, the step
  configuration overrides the pipeline.
---

# Configuration hierarchy

```python
from zenml import pipeline, step
from zenml.config import ResourceSettings


@step
def load_data(parameter: int) -> dict:
    ...

@step(settings={"resources": ResourceSettings(gpu_count=1, memory="2GB")})
def train_model(data: dict) -> None:
    ...


@pipeline(settings={"resources": ResourceSettings(cpu_count=2, memory="1GB")}) 
def simple_ml_pipeline(parameter: int):
    ...
    
# ZenMl merges the two configurations and uses the step configuration to override 
# values defined on the pipeline level

train_model.configuration.settings["resources"]
# -> cpu_count: 2, gpu_count=1, memory="2GB"

simple_ml_pipeline.configuration.settings["resources"]
# -> cpu_count: 2, memory="1GB"
```
