---
description: How to disable rich traceback output in ZenML.
---

# Disable `rich` traceback output

By default, ZenML uses the [`rich`](https://rich.readthedocs.io/en/stable/traceback.html) library to display rich traceback output. This is especially useful when debugging your pipelines. However, if you wish to disable this feature, you can do so by setting the following environment variable:

```bash
export ZENML_ENABLE_RICH_TRACEBACK=false
```

This will ensure that you see only the plain text traceback output.

Note that setting this on the [client environment](../../infrastructure-deployment/configure-python-environments/README.md#client-environment-or-the-runner-environment) (e.g. your local machine which runs the pipeline) will **not automatically disable rich tracebacks on remote pipeline runs**. That means setting this variable locally with only effect pipelines that run locally.

If you wish to disable it also for [remote pipeline runs](../../../user-guide/production-guide/cloud-orchestration.md), you can set the `ZENML_ENABLE_RICH_TRACEBACK` environment variable in your pipeline runs environment as follows:

```python
docker_settings = DockerSettings(environment={"ZENML_ENABLE_RICH_TRACEBACK": "false"})

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


