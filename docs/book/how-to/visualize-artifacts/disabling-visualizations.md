---
description: Disabling visualizations.
---

# Disabling Visualizations

If you would like to disable artifact visualization altogether, you can set `enable_artifact_visualization` at either pipeline or step level:

```python
@step(enable_artifact_visualization=False)
def my_step():
    ...

@pipeline(enable_artifact_visualization=False)
def my_pipeline():
    ...
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
