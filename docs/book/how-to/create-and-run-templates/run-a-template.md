---
description: Run a template
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Run a template

{% hint style="warning" %}
This is a [ZenML Pro](https://zenml.io/pro) only feature. Please 
[sign up here](https://cloud.zenml.io) get access.
{% endhint %}

<!-- ## Run a template from the dashboard -->

## Run a template in code

```python
from zenml.client import Client

template = Client().get_run_template(<NAME_OR_ID>)
config = template.config_template
# Optionally modify the config here

Client().trigger_pipeline(
    template_id=template.id,
    run_configuration=config,
)
```

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
