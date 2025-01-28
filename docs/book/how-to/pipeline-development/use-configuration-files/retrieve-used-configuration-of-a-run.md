# Find out which configuration was used for a run

Sometimes you might want to extract the used configuration from a pipeline that has already run. You can do this simply by loading the pipeline run and accessing its `config` attribute or the `config` attribute of one of its steps.

```python
from zenml.client import Client

pipeline_run = Client().get_pipeline_run(<PIPELINE_RUN_NAME>)

# General configuration for the pipeline
pipeline_run.config

# Configuration for a specific step
pipeline_run.steps[<STEP_NAME>].config
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
