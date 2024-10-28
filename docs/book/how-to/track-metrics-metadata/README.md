---
description: Tracking metrics and metadata
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# 📈 Track metrics and metadata

Logging metrics and metadata is standardized in ZenML. The most common pattern is to use the `log_xxx` methods, e.g.:

* Log metadata to a [model](attach-metadata-to-a-model.md): `log_model_metadata`
* Log metadata to an [artifact](attach-metadata-to-an-artifact.md): `log_artifact_metadata`
* Log metadata to a [step](attach-metadata-to-steps.md): `log_step_metadata`

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
