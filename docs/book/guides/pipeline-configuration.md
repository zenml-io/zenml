# Pipeline Configuration

## Setting step parameters using a config file

In addition to setting parameters for your pipeline steps in code, ZenML also allows you to use a configuration [yaml](https://yaml.org/) file.
This configuration file must follow the following structure:
```yaml
steps:
  step_name:
    parameters:
      parameter_name: parameter_value
      some_other_parameter_name: 2
  some_other_step_name:
    ...
```

Use the configuration file by calling the pipeline method `with_config(...)`:

```python
@pipeline
def my_pipeline(...):
    ...

pipeline_instance = my_pipeline(...).with_config("path_to_config.yaml")
pipeline_instance.run()
```

## Naming a pipeline run

When running a pipeline by calling `my_pipeline.run()`, ZenML uses the current date and time as the name for the pipeline run.
In order to change the name for a run, simply pass it as a parameter to the `run()` function:

```python
my_pipeline.run(run_name="custom_pipeline_run_name")
```

{% hint style="warning" %}
Pipeline run names must be unique, so make sure to compute it dynamically if you plan to run your pipeline multiple times.
{% endhint %}

Once the pipeline run is finished we can easily access this specific run during our post-execution workflow:

```python
from zenml.core.repo import Repository

repo = Repository()
pipeline = repo.get_pipeline(pipeline_name="my_pipeline")
run = pipeline.get_run(run_name="custom_pipeline_run_name")
```