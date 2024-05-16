# Enable or disable logs storing

By default, ZenML uses a special logging handler to capture the logs that occur during the execution of a step. These logs are stored within the respective artifact store of your stack.

```python
import logging

from zenml import step

@step 
def my_step() -> None:
    logging.warning("`Hello`")  # You can use the regular `logging` module.
    print("World.")  # You can utilize `print` statements as well. 
```

You can display the logs in the dashboard as follows:

![Displaying step logs on the dashboard](../../.gitbook/assets/zenml\_step\_logs.png)

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
2. Disable it by using the environmental variable `ZENML_DISABLE_STEP_LOGS_STORAGE` and setting it to `true`. This environmental variable takes precedence over the parameters mentioned above.
