# Enable or disable logs storing

By default, ZenML uses a logging handler to capture two types of logs:

* the logs collected from your ZenML client while triggering and waiting for a pipeline to run. These logs cover everything that happens client-side: building and pushing container images, triggering the pipeline, waiting for it to start, and waiting for it to finish. Note that these logs are not available for scheduled pipelines and the logs might not be available for pipeline runs that fail while building or pushing the container images.
* the logs collected from the execution of a step. These logs only cover what happens during the execution of a single step and originate mostly from the user-provided step code and the libraries it calls.

For step logs, users are free to use the default python logging module or print statements, and ZenML's logging handler will catch these logs and store them.

```python
import logging

from zenml import step

@step 
def my_step() -> None:
    logging.warning("`Hello`")  # You can use the regular `logging` module.
    print("World.")  # You can utilize `print` statements as well. 
```

All these logs are stored within the respective artifact store of your stack. You can visualize the pipeline run logs and step logs in the dashboard as follows:

![Displaying pipeline run logs on the dashboard](../../.gitbook/assets/zenml_pipeline_run_logs.png)
![Displaying step logs on the dashboard](../../.gitbook/assets/zenml_step_logs.png)

{% hint style="warning" %}
Note that if you are not connected to a cloud artifact store with a service connector configured then you will not
be able to view your logs in the dashboard. Read more [here](./view-logs-on-the-dasbhoard.md).
{% endhint %}

If you do not want to store the logs in your artifact store, you can do the following:

For pipeline run logs:

1.  Disable it by using the `enable_pipeline_logs` parameter with your `@pipeline` decorator:

    ```python
    from zenml import pipeline, step

    @pipeline(enable_pipeline_logs=False)  # disables logging for pipeline
    def my_pipeline():
        ...
    ```
2. Disable it by using the environmental variable `ZENML_DISABLE_PIPELINE_LOGS_STORAGE` and setting it to `true`. This environmental variable takes precedence over the parameter mentioned above. Note this environmental variable needs to be set on the [execution environment](../pipeline-development/configure-python-environments/README.md#execution-environments), i.e., on the orchestrator level:

```shell
export ZENML_DISABLE_PIPELINE_LOGS_STORAGE=true

python my_pipeline.py
```

For step logs:

1.  Disable it by using the `enable_step_logs` parameter either with your `@pipeline` or `@step` decorator:

    ```python
    from zenml import pipeline, step

    @step(enable_step_logs=False)  # disables logging for this step
    def my_step() -> None:
        ...

    @pipeline(enable_step_logs=False)  # disables logging for the entire pipeline
    def my_pipeline():
        ...
    ```
2. Disable it by using the environmental variable `ZENML_DISABLE_STEP_LOGS_STORAGE` and setting it to `true`. This environmental variable takes precedence over the parameters mentioned above. Note this environmental variable needs to be set on the [execution environment](../pipeline-development/configure-python-environments/README.md#execution-environments), i.e., on the orchestrator level:

```python
from zenml import pipeline
from zenml.config import DockerSettings

docker_settings = DockerSettings(environment={"ZENML_DISABLE_STEP_LOGS_STORAGE": "true"})

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