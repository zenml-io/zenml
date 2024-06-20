---
description: >-
  When things can be configured on the pipeline and step level, the step
  configuration overrides the pipeline.
---

# Configuration hierarchy

There are a few general rules when it comes to settings and configurations that are applied in multiple places. Generally the following is true:

* Configurations in code override configurations made inside of the yaml file
* Configurations at the step level override those made at the pipeline level
* In case of attributes the dictionaries are merged

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

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
