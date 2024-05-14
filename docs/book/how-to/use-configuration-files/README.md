---
description: ZenML makes it easy to configure and run a pipeline with configuration files.
---

# 📃 Use configuration files

These configuration files can help you set [parameters](../overview/how-to-use-pipeline-step-parameters.md), control [caching behavior ](../overview/how-to-control-caching-behavior.md)or even configure different stack components.

<pre class="language-yaml"><code class="lang-yaml">enable_cache: False
<strong>
</strong># Configure the pipeline parameters
parameters:
  dataset_name: "best_dataset"  
</code></pre>

```python
...

@pipeline  # This function combines steps together 
def simple_ml_pipeline(dataset_name: str):
    dataset = load_data()
    train_model(dataset)
    
if __name__=="__main__":
    simple_ml_pipeline.with_options(config_path=<INSERT_PATH_TO_CONFIG_YAML>)
```
