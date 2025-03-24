---
description: How to set the logging format in ZenML.
---

# Set logging format

If you want to change the default ZenML logging format, you can do so with the following environment variable:

```bash
export ZENML_LOGGING_FORMAT='%(asctime)s %(message)s'
```

The logging format must use the `%`-string formatting style. Check out [this page](https://docs.python.org/3/library/logging.html#logrecord-attributes) for all available attributes.

Note that setting this on the [client environment](../pipeline-development/configure-python-environments/README.md#client-environment-or-the-runner-environment) (e.g. your local machine which runs the pipeline) will **not automatically change the log format on remote pipeline runs**. That means setting this variable locally with only effect pipelines that run locally.

If you wish to configure it also for [remote pipeline runs](https://docs.zenml.io/user-guides/production-guide/cloud-orchestration), you can set the `ZENML_LOGGING_FORMAT` environment variable in your pipeline runs environment as follows:

```python
from zenml import pipeline
from zenml.config import DockerSettings

docker_settings = DockerSettings(environment={"ZENML_LOGGING_FORMAT": "%(asctime)s %(message)s"})

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


