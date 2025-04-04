---
description: How to disable step names from being displayed in logs.
---

# Disable step names in logs

By default, ZenML displays the current step name as a prefix in logs during pipeline execution to help you identify which step is currently running. For example:

```
[data_loader] Loading data from source...
[data_loader] Data loaded successfully.
[model_trainer] Training model with parameters...
```

It's important to note that these step name prefixes are only added to the console output and are not stored in the actual log files that ZenML saves. The stored logs will always be clean without the step name prefixes.

Disabling step names in logs is particularly useful when you have multiple pipeline steps running simultaneously, as the step prefixes can sometimes make the logs harder to read when steps are interleaved. In such cases, you might prefer clean logs without prefixes.

If you wish to disable this feature and have logs without step name prefixes, you can do so by setting the following environment variable:

```bash
ZENML_DISABLE_STEP_NAMES_IN_LOGS=true
```

Note that setting this on the [client environment](../pipeline-development/configure-python-environments/README.md#client-environment-or-the-runner-environment) (e.g. your local machine which runs the pipeline) will only affect locally executed pipelines. If you wish to disable step names in logs for remote pipeline runs, you can set the `ZENML_DISABLE_STEP_NAMES_IN_LOGS` environment variable in your pipeline runs environment as follows:

```python
from zenml import pipeline
from zenml.config import DockerSettings

docker_settings = DockerSettings(environment={"ZENML_DISABLE_STEP_NAMES_IN_LOGS": "true"})

# Either add it to the decorator
@pipeline(settings={"docker": docker_settings})
def my_pipeline() -> None:
    my_step()

# Or configure the pipelines options
my_pipeline = my_pipeline.with_options(
    settings={"docker": docker_settings}
)
```

When this option is enabled, logs will be displayed without step name prefixes, making them cleaner but potentially harder to associate with specific steps in your pipeline.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>