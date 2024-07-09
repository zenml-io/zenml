---
description: Learn how to delete pipelines.
---

# Delete a pipeline

## Delete the latest version of a pipeline

{% tabs %}
{% tab title="CLI" %}

```shell
zenml pipeline delete <PIPELINE_NAME>
```

{% endtab %}

{% tab title="Python SDK" %}

```python
from zenml.client import Client

Client().delete_pipeline(<PIPELINE_NAME>)
```

{% endtab %}

{% endtabs %}

## Delete a specific version of a pipeline

{% tabs %}
{% tab title="CLI" %}

```shell
zenml pipeline delete <PIPELINE_NAME> --version=<VERSION_NAME>
```

{% endtab %}

{% tab title="Python SDK" %}

```python
from zenml.client import Client

Client().delete_pipeline(<PIPELINE_NAME>, version=<VERSION_NAME>)
```

{% endtab %}

{% endtabs %}

## Delete all versions of a pipeline

{% tabs %}
{% tab title="CLI" %}

```shell
zenml pipeline delete <PIPELINE_NAME> --all-versions
```

{% endtab %}

{% tab title="Python SDK" %}

```python
from zenml.client import Client

Client().delete_pipeline(<PIPELINE_NAME>, all_versions=True)
```


{% endtab %}

{% endtabs %}

## Delete a pipeline run

Deleting a pipeline does not automatically delete any of its associated runs or artifacts. To delete a pipeline run, you can use the following command:

{% tabs %}
{% tab title="CLI" %}

```shell
zenml pipeline runs delete <RUN_NAME_OR_ID>
```

{% endtab %}

{% tab title="Python SDK" %}

```python
from zenml.client import Client

Client().delete_pipeline_run(<RUN_NAME_OR_ID>)
```


{% endtab %}

{% endtabs %}


<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
