---
description: Discover the power of caching with ZenML.
---

# Caching

Machine learning pipelines are rerun many times over throughout their development lifecycle. Prototyping is often a 
fast and iterative process that benefits a lot from caching. This makes caching a very powerful tool. (Read 
[our blogpost](https://blog.zenml.io/caching-ml-pipelines/) for more context on the benefits of caching.)

### Caching in ZenML

ZenML comes with caching enabled by default. As long as there is no change within a step or upstream from it, the 
cached outputs of that step will be used for the next pipeline run. This means that whenever there are code or 
configuration changes affecting a step, the step will be rerun in the next pipeline execution. Currently, the 
caching does not automatically detect changes within the file system or on external APIs. Make sure to set caching 
to `False` on steps that depend on external input or if the step should run regardless of caching.

There are multiple ways to take control of when and where caching is used.

### Caching on a Pipeline Level

On a pipeline level the caching policy can easily be set as a parameter within the decorator. If caching is explicitly 
turned off on a pipeline level, all steps are run without caching, even if caching is set to true for single 
steps.

```python
@pipeline(enable_cache=False)
def first_pipeline(....):
    """Pipeline with cache disabled"""
```

### Control Caching on a Step Level

Caching can also be explicitly turned off at a step level. You might want to turn off caching for steps that take 
external input (like fetching data from an API or File IO).

```python
@step(enable_cache=False)
def import_data_from_api(...):
    """Import most up-to-date data from public api"""
    ...
    
@pipeline(enable_cache=True)
def pipeline(....):
    """Pipeline with cache disabled"""
```

### Control Caching within the Runtime Configuration

Sometimes you want to have control over caching at runtime instead of defaulting to the backed in configurations of 
your pipeline and its steps. ZenML offers a way to override all caching settings of the pipeline at runtime.

```python
first_pipeline(step_1=..., step_2=...).run(enable_cache=False)
```

### Summary in Code

<details>
    <summary>Code Example of this Section</summary>

```python
from zenml.steps import step, Output, BaseStepConfig
from zenml.pipelines import pipeline

@step
def my_first_step() -> Output(output_int=int, output_float=float):
    """Step that returns a pre-defined integer and float"""
    return 7, 0.1

@step(enable_cache=False)
def my_second_step(input_int: int, input_float: float
                   ) -> Output(output_int=int, output_float=float):
    """Step that doubles the inputs"""
    return 2 * input_int, 2 * input_float

class SecondStepConfig(BaseStepConfig):
    """Trainer params"""
    multiplier: int = 4

@step
def my_configured_step(config: SecondStepConfig, input_int: int,
                       input_float: float
                       ) -> Output(output_int=int, output_float=float):
    """Step that multiply the inputs"""
    return config.multiplier * input_int, config.multiplier * input_float

@pipeline
def first_pipeline(
        step_1,
        step_2
):
    output_1, output_2 = step_1()
    step_2(output_1, output_2)

first_pipeline(step_1=my_first_step(),
               step_2=my_second_step()
               ).run()

# Step one will use cache, Step two will be rerun due to decorator config
first_pipeline(step_1=my_first_step(),
               step_2=my_second_step()
               ).run()

# Complete pipeline will be rerun
first_pipeline(step_1=my_first_step(),
               step_2=my_second_step()
               ).run(enable_cache=False)

first_pipeline(step_1=my_first_step(),
               step_2=my_configured_step(SecondStepConfig(multiplier=11))
               ).run()

# Step one will use cache, Step two is rerun as the config changed
first_pipeline(step_1=my_first_step(),
               step_2=my_configured_step(SecondStepConfig(multiplier=13))
               ).run()
```
</details>
