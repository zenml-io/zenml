---
description: How to disable colorful logging in ZenML.
---

# Disable colorful logging

By default, ZenML uses colorful logging to make it easier to read logs. However, if you wish to disable this feature, you can do so by setting the following environment variable:

```bash
ZENML_LOGGING_COLORS_DISABLED=true
```

Note that setting this on your local machine will automatically disable colorful logging on remote orchestrators. If you wish to disable it locally, but turn on for remote orchestrators, you can set the `ZENML_LOGGING_COLORS_DISABLED` environment variable in your orchestrator's environment as follows:

```python
docker_settings = DockerSettings(environment={"ZENML_LOGGING_COLORS_DISABLED": "false"})

# Either add it to the decorator
@pipeline(settings={"docker": docker_settings})
def my_pipeline() -> None:
    my_step()

# Or configure the pipelines options
my_pipeline = my_pipeline.with_options(
    settings={"docker": docker_settings}
)
```

