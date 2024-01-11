---
description: Configure your pipeline.
---

# Configure your pipeline

Now that we have our pipeline up and running in the cloud, you might be wondering how ZenML figured out what sort of dependencies to install
in the docker image that we just ran on the VM. The answer lies in the [runner script we executed (i.e. run.py)](https://github.com/zenml-io/zenml/blob/main/examples/quickstart/run.py#L215), in particular these lines:

```python
pipeline_args["config_path"] = os.path.join(
    config_folder, "training_rf.yaml"
)
# Configure the pipeline
training_pipeline_configured = training_pipeline.with_options(**pipeline_args)
# Create a run
training_pipeline_configured()
```

The above commands [configure our training pipeline](../starter-guide/create-an-ml-pipeline.md#configure-with-a-yaml-file) with a YAML configuration called `training_rf.yaml` (found [here in the source code](https://github.com/zenml-io/zenml/blob/main/examples/quickstart/configs/training_rf.yaml)). Let's learn more about this configuration file.

{% hint style="info" %}
The `with_options` command that points to a YAML config is only one way to configure a pipeline. We can also directly configure a pipeline or a step in the decorator:

```python
@pipeline(settings=...)
```

However, it is best to not mix configuration from code to ensure seperation of concerns in our codebase.
{% endhint %}

## Important settings of a pipeline

This section of the production guide will be about best practices on how to configure a pipeline in production. Until this section is ready, here are some useful links to achieve this goal:

- [Settings in ZenML](../advanced-guide/pipelining-features/configure-steps-pipelines.md)
- [Using a YAML configuration](../advanced-guide/pipelining-features/configure-steps-pipelines.md#settings-in-zenml)
- [The step operator in ZenML](../../stacks-and-components/component-guide/step-operators/step-operators.md)
- [Containerization of a pipeline](../advanced-guide/infrastructure-management/containerize-your-pipeline.md)
- [Specify resource requirements for steps](../advanced-guide/infrastructure-management/scale-compute-to-the-cloud.md)

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>