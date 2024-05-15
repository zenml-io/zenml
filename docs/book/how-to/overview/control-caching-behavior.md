---
description: >-
  By default steps in ZenML pipelines are cached whenever code and parameters
  stay unchanged.
---

# Control caching behavior

```python
@step(enable_cache=True) # set cache behavior at step level
def load_data(parameter: int) -> dict:
    ...

@step(enable_cache=False) # settings at step level override pipeline level
def train_model(data: dict) -> None:
    ...

@pipeline(enable_cache=True) # set cache behavior at step level
def simple_ml_pipeline(parameter: int):
    ...
```

{% hint style="info" %}
Caching only happens when code and parameters stay the same.
{% endhint %}

Like many other step and pipeline settings, you can also change this afterwards:

```python
# Same as passing it in the step decorator
my_step.configure(enable_cache=...)

# Same as passing it in the pipeline decorator
my_pipeline.configure(enable_cache=...)
```

For configuring this in a separate yaml file, check out the relevant documentation [here](../use-configuration-files/).