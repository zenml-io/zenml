# Enable or disable logs storing

By default, ZenML uses a logging handler to capture the logs that occur during the execution of a step. Users are free to use the default python logging module or print statements, and ZenML's logging handler will catch these logs and store them. 

```python
import logging

from zenml import step

@step 
def my_step() -> None:
    logging.warning("`Hello`")  # You can use the regular `logging` module.
    print("World.")  # You can utilize `print` statements as well. 
```

These logs are stored within the respective artifact store of your stack. You can display the logs in the dashboard as follows:

![Displaying step logs on the dashboard](../../.gitbook/assets/zenml\_step\_logs.png)

{% hint style="warning" %}
Note that if you are not connected to a cloud artifact store with a service connector configured then you will not
be able to view your logs in the dashboard. Read more [here](./view-logs-on-the-dasbhoard.md).
{% endhint %}

If you do not want to store the logs in your artifact store, you can:

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
2. Disable it by using the environmental variable `ZENML_DISABLE_STEP_LOGS_STORAGE` and setting it to `true`. This environmental variable takes precedence over the parameters mentioned above. Note this environmental variable needs to be set on the [execution environment](../configure-python-environments/README.md#execution-environments), i.e., on the orchestrator level:

```python
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