---
description: Learn how to delete artifacts.
---

# Delete an artifact

There is currently no way to delete an artifact directly, because it may lead to
a broken state of the ZenML database (dangling references to pipeline runs that produce artifacts).

However, it is possible to delete artifacts that are no longer referenced by any pipeline runs:

```shell
zenml artifact prune
```

By default, this method deletes artifacts physically from the underlying [artifact store](../../component-guide/artifact-stores/artifact-stores.md)
AND also the entry in the database. You can control this behavior by using the `--only-artifact` and `--only-metadata` flags.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
