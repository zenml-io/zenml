---
description: Naming your pipeline runs makes them easy to use for post execution workflows
---

# Naming a pipeline run

When running a pipeline by calling `my_pipeline.run()`, ZenML uses the current date and time as the name for the 
pipeline run. In order to change the name for a run, simply pass it as a parameter to the `run()` function:

```python
my_pipeline.run(run_name="custom_pipeline_run_name")
```

{% hint style="warning" %}
Pipeline run names must be unique, so make sure to compute it dynamically if you plan to run your pipeline multiple 
times.
{% endhint %}

Once the pipeline run is finished we can easily access this specific run during our post-execution workflow:

```python
from zenml.repository import Repository

repo = Repository()
pipeline = repo.get_pipeline(pipeline_name="my_pipeline")
run = pipeline.get_run("custom_pipeline_run_name")
```
