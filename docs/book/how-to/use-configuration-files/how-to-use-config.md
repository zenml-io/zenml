---
description: Specify a configuration file
---

# 📃 Use configuration files

{% hint style="info" %}
All configuration that can be specified in a YAML file can also be specified in code itself.
However, it is best practice to use a YAML file to separate config from code.
{% endhint %}

You can use the `with_options(config_path=<PATH_TO_CONFIG>)` pattern to apply your
configuration to a pipeline. Here is a minimal example of using a file based configuration yaml.

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

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>