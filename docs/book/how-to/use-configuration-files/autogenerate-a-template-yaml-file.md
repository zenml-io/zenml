---
description: >-
  To help you figure out what you can put in your configuration file, simply
  autogenerate a template.
---

# Autogenerate a template yaml file

```python
from zenml import pipeline
...

@pipeline(enable_cache=True) # set cache behavior at step level
def simple_ml_pipeline(parameter: int):
    dataset = load_data(parameter=parameter)
    train_model(dataset)

simple_ml_pipeline.write_run_configuration_template(path=<Insert_path_here>)
```

{% hint style="info" %}
When you want to configure your pipeline with a certain stack in mind, you can do so as well:\
\`...write\_run\_configuration\_template(stack=\<Insert\_stack\_here>)
{% endhint %}
