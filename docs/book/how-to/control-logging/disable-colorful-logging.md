---
description: How to disable colorful logging in ZenML.
---

# Disable colorful logging

By default, ZenML uses colorful logging to make it easier to read logs. However, if you wish to disable this feature, you can do so by setting the following environment variable:

```bash
ZENML_LOGGING_COLORS_DISABLED=true
```

Note that setting this on the [client environment](../pipeline-development/configure-python-environments/README.md#client-environment-or-the-runner-environment) (e.g. your local machine which runs the pipeline) will automatically disable colorful logging on remote pipeline runs. If you wish to only disable it locally, but turn on for remote pipeline runs, you can set the `ZENML_LOGGING_COLORS_DISABLED` environment variable in your pipeline runs environment as follows:

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

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>