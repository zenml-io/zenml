---
description: ZenML makes it easy to configure and run a pipeline with configuration files.
---

# 📃 Use configuration files

Configuration files can help you set [parameters](../overview/use-pipeline-step-parameters.md), control [caching behavior ](../overview/control-caching-behavior.md)or even configure different stack components.

<pre class="language-yaml"><code class="lang-yaml">enable_cache: False
<strong>
</strong># Configure the pipeline parameters
parameters:
  dataset_name: "best_dataset"  
  
steps:
  load_data:  # Use the step name here
    enable_cache: False  # same as @step(enable_cache=False)
</code></pre>

```python
@step
def load_data(parameter: int) -> dict:
    ...

@pipeline  # This function combines steps together 
def simple_ml_pipeline(dataset_name: str):
    ...
    
if __name__=="__main__":
    simple_ml_pipeline.with_options(config_path=<INSERT_PATH_TO_CONFIG_YAML>)
```
