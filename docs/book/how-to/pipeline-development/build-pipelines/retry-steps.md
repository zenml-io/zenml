---
description: Automatically configure your steps to retry if they fail.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Allow step retry in case of failure

ZenML provides a built-in retry mechanism that allows you to configure automatic retries for your steps in case of failures. This can be useful when dealing with intermittent issues or transient errors. A common pattern when trying to run a step on GPU-backed hardware is that the provider will not have enough resources available, so you can set ZenML to handle the retries until the resources free up. You can configure three parameters for step retries:

* **max_retries:** The maximum number of times the step should be retried in case of failure.
* **delay:** The initial delay in **seconds** before the first retry attempt.
* **backoff:** The factor by which the delay should be multiplied after each retry attempt.

## Using the @step decorator:

You can specify the retry configuration directly in the definition of your step as follows:

```python
from zenml.config.retry_config import StepRetryConfig

@step(
    retry=StepRetryConfig(
        max_retries=3, 
        delay=10, 
        backoff=2
    )
)
def my_step() -> None:
    raise Exception("This is a test exception")
steps:
  my_step:
    retry:
      max_retries: 3
      delay: 10
      backoff: 2
```

{% hint style="info" %}
Note that infinite retries are not supported at the moment. If you set `max_retries` to a very large value or do not specify it at all, ZenML will still enforce an internal maximum number of retries to prevent infinite loops. We recommend setting a reasonable `max_retries` value based on your use case and the expected frequency of transient failures.
{% endhint %}

***

### See Also:

<table data-view="cards"><thead><tr><th></th><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td>Failure/Success Hooks</td><td></td><td></td><td><a href="use-failure-success-hooks.md">use-failure-success-hooks.md</a></td></tr><tr><td>Configure pipelines</td><td></td><td></td><td><a href="../../pipeline-development/use-configuration-files/how-to-use-config.md">./use-configuration-files/how-to-use-config.md</a></td></tr></tbody></table>

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>