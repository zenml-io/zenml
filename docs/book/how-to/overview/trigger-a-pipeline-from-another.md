---
description: >-
  When writing your pipelines you can also always call a pipeline from within
  another.
---

# Trigger a pipeline from another

```python
@pipeline
def date_loader_pipeline(...) -> dict:
    ...
    return {...}

@pipeline  
def simple_ml_pipeline():
    dataset = date_loader_pipeline() # this executes all the steps of this pipeline and gets the return value
    train_model(dataset)
```

{% hint style="info" %}
Calling a pipeline inside another pipeline does not actually trigger a separate run of the child pipeline but instead invokes the steps of the child pipeline to the parent pipeline.
{% endhint %}