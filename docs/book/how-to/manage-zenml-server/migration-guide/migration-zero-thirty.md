---
description: How to migrate from ZenML 0.20.0-0.23.0 to 0.30.0-0.39.1.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


{% hint style="warning" %}
Migrating to `0.30.0` performs non-reversible database changes so downgrading
to `<=0.23.0` is not possible afterwards. If you are running on an older ZenML 
version, please follow the 
[0.20.0 Migration Guide](migration-zero-twenty.md) first to prevent unexpected
database migration failures.
{% endhint %}

The ZenML 0.30.0 release removed the `ml-pipelines-sdk` dependency in favor of
natively storing pipeline runs and artifacts in the ZenML database. The
corresponding database migration will happen automatically as soon as you run
any `zenml ...` CLI command after installing the new ZenML version, e.g.:

```bash
pip install zenml==0.30.0
zenml version  # 0.30.0
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
