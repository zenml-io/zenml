---
description: Create run templates for running pipelines from the server
---

# Create a run template from a previous pipeline run

{% hint style="warning" %}
This is a [ZenML Pro](https://zenml.io/pro) only feature. Please 
[sign up here](https://cloud.zenml.io) get access.

The creation of a run template from a pipeline run **only** 
works for runs that were executed on a remote stack (i.e. at least a remote 
orchestrator, artifact store, and container registry).
{% endhint %}

<!-- ## Create a template from the dashboard -->

## Create a template in code

```python
from zenml.client import Client

run = Client().get_pipeline_run(<RUN_NAME_OR_ID>)
Client().create_run_template(
    name=<NAME>,
    deployment_id=run.deployment_id
)
```

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
