---
description: The best way to trigger a pipeline run so that it runs in the background
---

# Run pipelines asynchronously in the background

yes you can pass the `synchronous=False` when you configure your orchestrator

ep it’s a orchestrator setting, which means you can specify it either when registering the stack component but also override it at runtime for certain pipelines:

```
@pipeline(settings = {"orchestrator.kubernetes": {"synchronous": False}})
def my_pipeline():
  ...
```

or in a yaml config file:\


```
settings:
  orchestrator.kubernetes:
    synchronous: false
```
