---
description: Add more resources to your pipeline configuration.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Configure your pipeline to add compute

Now that we have our pipeline up and running in the cloud, you might be wondering how ZenML figured out what sort of dependencies to install in the Docker image that we just ran on the VM. The answer lies in the [runner script we executed (i.e. run.py)](https://github.com/zenml-io/zenml/blob/main/examples/quickstart/run.py#L215), in particular, these lines:

```python
pipeline_args["config_path"] = os.path.join(
    config_folder, "training_rf.yaml"
)
# Configure the pipeline
training_pipeline_configured = training_pipeline.with_options(**pipeline_args)
# Create a run
training_pipeline_configured()
```

The above commands [configure our training pipeline](../starter-guide/create-an-ml-pipeline.md#configure-with-a-yaml-file) with a YAML configuration called `training_rf.yaml` (found [here in the source code](https://github.com/zenml-io/zenml/blob/main/examples/quickstart/configs/training\_rf.yaml)). Let's learn more about this configuration file.

{% hint style="info" %}
The `with_options` command that points to a YAML config is only one way to configure a pipeline. We can also directly configure a pipeline or a step in the decorator:

```python
@pipeline(settings=...)
```

However, it is best to not mix configuration from code to ensure separation of concerns in our codebase.
{% endhint %}

## Breaking down our configuration YAML

The YAML configuration of a ZenML pipeline can be very simple, as in this case. Let's break it down and go through each section one by one:

### The Docker settings

```yaml
settings:
  docker:
    required_integrations:
      - sklearn
    requirements:
      - pyarrow
```

The first section is the so-called `settings` of the pipeline. This section has a `docker` key, which controls the [containerization process](cloud-orchestration.md#orchestrating-pipelines-on-the-cloud). Here, we are simply telling ZenML that we need `pyarrow` as a pip requirement, and we want to enable the `sklearn` integration of ZenML, which will in turn install the `scikit-learn` library. This Docker section can be populated with many different options, and correspond to the [DockerSettings](https://sdkdocs.zenml.io/latest/core\_code\_docs/core-config/#zenml.config.docker\_settings.DockerSettings) class in the Python SDK.

### Associating a ZenML Model

The next section is about associating a [ZenML Model](../starter-guide/track-ml-models.md) with this pipeline.

```yaml
# Configuration of the Model Control Plane
model:
  name: breast_cancer_classifier
  version: rf
  license: Apache 2.0
  description: A breast cancer classifier
  tags: ["breast_cancer", "classifier"]
```

You will see that this configuration lines up with the model created after executing these pipelines:

{% tabs %}
{% tab title="CLI" %}
```shell
# List all versions of the breast_cancer_classifier
zenml model version list breast_cancer_classifier
```
{% endtab %}

{% tab title="Dashboard" %}
[ZenML Pro](https://www.zenml.io/pro) ships with a Model Control Plane dashboard where you can visualize all the versions:

<figure><img src="../../.gitbook/assets/mcp_model_versions_list.png" alt=""><figcaption><p>All model versions listed</p></figcaption></figure>
{% endtab %}
{% endtabs %}

### Passing parameters

The last part of the config YAML is the `parameters` key:

```yaml
# Configure the pipeline
parameters:
  model_type: "rf"  # Choose between rf/sgd
```

This parameters key aligns with the parameters that the pipeline expects. In this case, the pipeline expects a string called `model_type` that will inform it which type of model to use:

```python
@pipeline
def training_pipeline(model_type: str):
    ...
```

So you can see that the YAML config is fairly easy to use and is an important part of the codebase to control the execution of our pipeline. You can read more about how to configure a pipeline in the [how to section](../../how-to/use-configuration-files/what-can-be-configured.md), but for now, we can move on to scaling our pipeline.

## Scaling compute on the cloud

When we ran our pipeline with the above config, ZenML used some sane defaults to pick the resource requirements for that pipeline. However, in the real world, you might want to add more memory, CPU, or even a GPU depending on the pipeline at hand.

This is as easy as adding the following section to your local `training_rf.yaml` file:

```yaml
# These are the resources for the entire pipeline, i.e., each step
settings:    
  ...

  # Adapt this to vm_azure or vm_gcp accordingly
  orchestrator.vm_aws:
    memory: 32 # in GB
        
...    
steps:
  model_trainer:
    settings:
      orchestrator.vm_aws:
        cpus: 8
```

Here we are configuring the entire pipeline with a certain amount of memory, while for the trainer step we are additionally configuring 8 CPU cores. The `orchestrator.vm_aws` key corresponds to the [`SkypilotBaseOrchestratorSettings`](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-skypilot/#zenml.integrations.skypilot.flavors.skypilot\_orchestrator\_base\_vm\_config.SkypilotBaseOrchestratorSettings) class in the Python SDK. You can adapt it to `vm_gcp` or `vm_azure` depending on which flavor of skypilot you have configured.

{% hint style="info" %}
Read more about settings in ZenML [here](../../how-to/use-configuration-files/runtime-configuration.md).
{% endhint %}

Now let's run the pipeline again:

```python
python run.py --training-pipeline
```

Now you should notice the machine that gets provisioned on your cloud provider would have a different configuration as compared to last time. As easy as that!

Bear in mind that not every orchestrator supports `ResourceSettings` directly. To learn more, you can read about [`ResourceSettings` here](../../how-to/use-configuration-files/runtime-configuration.md), including the ability to [attach a GPU](../../how-to/training-with-gpus/training-with-gpus.md#1-specify-a-cuda-enabled-parent-image-in-your-dockersettings).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
