---
description: >-
  Building pipelines is as simple as adding the `@step` and `@pipeline`
  decorators to your code.
---

# Build a pipeline?

```python
from zenml import step, pipeline

@step 
def my_step:
    return None
    

@pipeline
def my_pipeline():
    my_step()
```

Check below for more advanced pipelining features.

<table data-view="cards"><thead><tr><th></th><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td>Configure pipeline/step parameters</td><td></td><td></td><td><a href="how-to-configure-pipeline-step-parameters.md">how-to-configure-pipeline-step-parameters.md</a></td></tr><tr><td>Control caching behavior</td><td></td><td></td><td><a href="how-to-control-caching-behavior.md">how-to-control-caching-behavior.md</a></td></tr><tr><td></td><td></td><td></td><td></td></tr></tbody></table>
