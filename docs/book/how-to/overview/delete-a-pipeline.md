---
description: Learn how to delete pipelines.
---

# Delete a pipeline

## Delete the latest version of a pipeline

```shell
zenml pipeline delete <PIPELINE_NAME>
```

## Delete a specific version of a pipeline

```shell
zenml pipeline delete <PIPELINE_NAME> --version=<VERSION_NAME>
```

## Delete all versions of a pipeline

```shell
zenml pipeline delete <PIPELINE_NAME> --all-versions
```

## Delete a pipeline run

Deleting a pipeline does not automatically delete any of its associated runs or artifacts. To delete a pipeline run, you can use the following command:

```shell
zenml pipeline runs delete <RUN_NAME_OR_ID>
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
