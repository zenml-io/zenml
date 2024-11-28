---
description: Create a template using the ZenML CLI
---

{% hint style="success" %}
This is a [ZenML Pro](https://zenml.io/pro)-only feature. Please
[sign up here](https://cloud.zenml.io) to get access.
{% endhint %}

## Create a template

You can use the ZenML CLI to create a run template:

```bash
# The <PIPELINE_SOURCE_PATH> will be `run.my_pipeline` if you defined a
# pipeline with name `my_pipeline` in a file called `run.py`
zenml pipeline create-run-template <PIPELINE_SOURCE_PATH> --name=<TEMPLATE_NAME>
```

{% hint style="warning" %}
You need to have an active **remote stack** while running this command or you can specify
one with the `--stack` option.
{% endhint %}


<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>

