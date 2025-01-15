---
description: How to set the logging format in ZenML.
---

# Set logging format

If you want to change the default ZenML logging format, you can do so with the following environment variable:

```bash
export ZENML_LOGGING_FORMAT='%(asctime)s %(message)s'
```

Check out [this page](https://docs.python.org/3/library/logging.html#logrecord-attributes) for all available attributes.

{% hint style="info" %}
Setting this environment variable in the [client environment](../pipeline-development/configure-python-environments/README.md#client-environment-or-the-runner-environment) (e.g. your local machine which runs the pipeline) will **automatically set the same logging verbosity for remote pipeline runs**.
{% endhint %}

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


