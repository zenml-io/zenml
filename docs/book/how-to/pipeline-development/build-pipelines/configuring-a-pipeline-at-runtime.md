---
description: Configuring a pipeline at runtime.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Runtime configuration of a pipeline run

It is often the case that there is a need to run a pipeline with a different configuration.
In this case, you should in most cases use the [`pipeline.with_options`](../../pipeline-development/use-configuration-files/README.md) method. You can do this:

1. Either by explicitly configuring options like `with_options(steps="trainer": {"parameters": {"param1": 1}})`
2. Or by passing a YAML file using `with_options(config_file="path_to_yaml_file")`.

You can learn more about these options [here](../../pipeline-development/use-configuration-files/README.md).

However, there is one exception: if you would like to trigger a pipeline from the client
or another pipeline, you would need to pass the `PipelineRunConfiguration` object.
Learn more about this [here](../../pipeline-development/trigger-pipelines/use-templates-python.md#advanced-usage-run-a-template-from-another-pipeline).

<table data-view="cards"><thead><tr><th></th><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td>Using config files</td><td></td><td></td><td><a href="../../pipeline-development/use-configuration-files/README.md">../../pipeline-development/use-configuration-files/README.md</a></td></tr></tbody></table>

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>