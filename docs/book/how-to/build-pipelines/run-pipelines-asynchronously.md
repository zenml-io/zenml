---
description: The best way to trigger a pipeline run so that it runs in the background
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Run pipelines asynchronously

By default your pipelines will run synchronously. This means your terminal will follow along the logs as the pipeline is being built/runs.&#x20;

This behavior can be changed in multiple ways. Either the orchestrator can be configured to always run asynchronously by setting `synchronous=False`. The other option is to temporarily set this at the pipeline configuration level during runtime.

```python
from zenml import pipeline

@pipeline(settings = {"orchestrator.<STACK_NAME>": {"synchronous": False}})
def my_pipeline():
  ...
```

or in a yaml config file:

```yaml
settings:
  orchestrator.<STACK_NAME>:
    synchronous: false
```

***

<table data-view="cards"><thead><tr><th></th><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td>Learn more about orchestrators here</td><td></td><td></td><td><a href="../../component-guide/orchestrators/orchestrators.md">orchestrators.md</a></td></tr></tbody></table>
<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


