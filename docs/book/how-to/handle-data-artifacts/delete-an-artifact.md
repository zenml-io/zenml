---
description: Learn how to delete artifacts.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Delete an artifact

There is currently no way to delete an artifact directly, because it may lead to
a broken state of the ZenML database (dangling references to pipeline runs that produce artifacts).

However, it is possible to delete artifacts that are no longer referenced by any pipeline runs:

```shell
zenml artifact prune
```

By default, this method deletes artifacts physically from the underlying [artifact store](../../component-guide/artifact-stores/artifact-stores.md)
AND also the entry in the database. You can control this behavior by using the
`--only-artifact` and `--only-metadata` flags.

You might find that some artifacts throw errors when you try to prune them,
likely because they were stored locally and no longer exist. If you wish to
continue pruning and to ignore these errors, please add the `--ignore-errors`
flag. Warning messages will still be output to the terminal during this process.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
