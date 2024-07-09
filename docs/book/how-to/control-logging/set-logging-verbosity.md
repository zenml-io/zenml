---
description: How to set the logging verbosity in ZenML.
---

# Set logging verbosity

By default, ZenML sets the logging verbosity to `INFO`. If you wish to change this, you can do so by setting the following environment variable:

```bash
export ZENML_LOGGING_VERBOSITY=INFO
```

Choose from `INFO`, `WARN`, `ERROR`, `CRITICAL`, `DEBUG`. This will set the logs
to whichever level you suggest.

Note that setting this on the [client environment](../configure-python-environments/README.md#client-environment-or-the-runner-environment) (e.g. your local machine which runs the pipeline) will **not automatically set the same logging verbosity for remote pipeline runs**. That means setting this variable locally with only effect pipelines that run locally.

If you wish to control for [remote pipeline runs](../../user-guide/production-guide/cloud-orchestration.md), you can set the `ZENML_LOGGING_VERBOSITY` environment variable in your pipeline runs environment as follows:

```python
docker_settings = DockerSettings(environment={"ZENML_LOGGING_VERBOSITY": "DEBUG"})

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


