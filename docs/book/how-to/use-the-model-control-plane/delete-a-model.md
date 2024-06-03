---
description: Learn how to delete pipelines.
---

# Delete a model

Deleting a model or a specific model version means removing all links between the Model entity
and artifacts + pipeline runs, and will also delete all metadata associated with that Model.

## Deleting all versions of a model

```shell
zenml model delete <MODEL_NAME>
```

## Delete a specific version of a model

```shell
zenml model delete <MODEL_NAME> <MODEL_VERSION_NAME>
```


<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
