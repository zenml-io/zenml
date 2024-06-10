---
description: >-
  By default steps in ZenML pipelines are cached whenever code and parameters
  stay unchanged.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


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

Like many other step and pipeline settings, you can also change this afterward:

```python
# Same as passing it in the step decorator
my_step.configure(enable_cache=...)

# Same as passing it in the pipeline decorator
my_pipeline.configure(enable_cache=...)
```

***

<table data-view="cards"><thead><tr><th></th><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td>Find out here how to configure this in a YAML file</td><td></td><td></td><td><a href="../use-configuration-files/">use-configuration-files</a></td></tr></tbody></table>
<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


