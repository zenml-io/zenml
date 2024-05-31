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
be able to view your logs in the dashboard.
{% endhint %}

If you do not want to store the logs for your pipeline (for example due to performance reduction or storage limits),
you can follow [these instructions](./enable-or-disable-logs-storing.md).
You can control logging verbosity following [this guide](./set-logging-verbosity.md).


<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>