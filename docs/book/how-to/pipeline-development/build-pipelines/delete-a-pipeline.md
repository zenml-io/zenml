---
description: Learn how to delete pipelines.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Delete a pipeline

In order to delete a pipeline, you can either use the CLI or the Python SDK:

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

{% hint style="info" %}
Deleting a pipeline does not automatically delete any of its associated runs or 
artifacts.
{% endhint %}

If you want to delete multiple pipelines at once, you might find the Python SDK
preferable. If you have pipelines with the same prefix, you will need to pass in
the `id` of each pipeline separately so ZenML is able to identify them. In this
case, you could use a script like the following:

```python
from zenml.client import Client

client = Client()

# Get the list of pipelines that start with "test_pipeline"
# use a large size to ensure we get all of them
pipelines_list = client.list_pipelines(name="startswith:test_pipeline", size=100)

target_pipeline_ids = [p.id for p in pipelines_list.items]

print(f"Found {len(target_pipeline_ids)} pipelines to delete")

confirmation = input("Do you really want to delete these pipelines? (y/n): ").lower()

if confirmation == 'y':
    print(f"Deleting {len(target_pipeline_ids)} pipelines")
    for pid in target_pipeline_ids:
        client.delete_pipeline(pid)
    print("Deletion complete")
else:
    print("Deletion cancelled")
```

## Delete a pipeline run

To delete a pipeline run, you can use the following CLI command or the client:

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
