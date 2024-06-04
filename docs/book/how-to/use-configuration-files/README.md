---
description: ZenML makes it easy to configure and run a pipeline with configuration files.
---

# 📃 Use configuration files

ZenML pipelines can be configured at runtime with a simple YAML file that can help you set [parameters](../build-pipelines/use-pipeline-step-parameters.md), control [caching behavior](../build-pipelines/control-caching-behavior.md) or even configure different stack components.

{% hint style="info" %}
All configuration that can be specified in a YAML file can also be specified in code itself.
However, it is best practice to use a YAML file to separate config from code.
{% endhint %}

Here is a minimal example of using a file based configuration yaml.

```yaml
enable_cache: False

# Configure the pipeline parameters
parameters:
  dataset_name: "best_dataset"  
  
steps:
  load_data:  # Use the step name here
    enable_cache: False  # same as @step(enable_cache=False)
```

```python
from zenml import step, pipeline

@step
def load_data(dataset_name: str) -> dict:
    ...

@pipeline  # This function combines steps together 
def simple_ml_pipeline(dataset_name: str):
    load_data(dataset_name)
    
if __name__=="__main__":
    simple_ml_pipeline.with_options(config_path=<INSERT_PATH_TO_CONFIG_YAML>)()
```

The above would run the `simple_ml_pipeline` with cache disabled for `load_data` and the parameter
`dataset_name` set to `best_dataset`.

Learn more about the different options in the following sections:

<table data-view="cards"><thead><tr><th></th><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td>What can be configured</td><td></td><td></td><td><a href="what-can-be-configured.md">what-can-be-configured.md</a></td></tr><tr><td>Configuration hierarchy</td><td></td><td></td><td><a href="configuration-hierarchy.md">configuration-hierarchy.md</a></td></tr><tr><td>Autogenerate a template yaml file</td><td></td><td></td><td><a href="autogenerate-a-template-yaml-file.md">autogenerate-a-template-yaml-file.md</a></td></tr></tbody></table>

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
