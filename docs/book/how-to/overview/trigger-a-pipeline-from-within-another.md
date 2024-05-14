---
description: >-
  When writing your pipelines you can also always call a pipeline from within
  another.
---

# Trigger a pipeline from within another

```python
@pipeline
def date_loader_pipeline(...):
    ...

@pipeline  
def simple_ml_pipeline():
    dataset = date_loader_pipeline()
    train_model(dataset)
```
