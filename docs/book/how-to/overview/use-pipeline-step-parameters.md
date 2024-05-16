---
description: >-
  Steps and pipelines can be parameterized just like any other python function
  that you are familiar with.
---

# Use pipeline/step parameters

```python
from zenml import pipeline, step

@step
def load_data(parameter: int) -> dict:
    # use the parameter here

@step
def train_model(data: dict) -> None:
    # Train some model here


@pipeline  
def simple_ml_pipeline(parameter: int):
    dataset = load_data(parameter=parameter)
    train_model(dataset)


# You can set the parameter on the step at a later point
load_data.configure(parameters={"parameter": 42})

# For parameters on the pipeline level, you can also choose a 
# parameter when running the pipeline
simple_ml_pipeline(parameter=42)
```

{% hint style="info" %}
You can also use a configuration file to set the parameters. The configuration file would look like this.
{% endhint %}

```python
# config.yaml

# these are parameters of the pipeline
parameters:
  parameter: 42

steps:
  load_data:
    # these are parameters of the step `my_step`
    parameters:
      parameter: 42
```

```python
# Run the pipeline with the 
simple_ml_pipeline.with_options(config_path=<INSERT_PATH_TO_CONFIG_YAML>)
```
