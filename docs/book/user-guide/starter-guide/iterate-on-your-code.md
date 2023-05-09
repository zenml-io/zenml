---
description: Iterate quickly with ZenML through fast caching.
---

# Speed up with Caching

ZenML tries its best to get out of the way as you run your ML experiments. For this, it has built in  caching support to help your local work be as fast as possible.

In the logs of your previous runs you might have noticed at this point that rerunning the pipeline a second time will use caching on the steps:

{% tabs %}
{% tab title="Logs" %}
```bash
Step step_1 has started.
Using cached version of step_1.
Step step_2 has started.
Using cached version of step_2.
```
{% endtab %}

{% tab title="Dashboard" %}
<figure><img src="../../.gitbook/assets/cached_run_dashboard.png" alt=""><figcaption><p>DAG of a cached pipeline run</p></figcaption></figure>
{% endtab %}
{% endtabs %}

This is because ZenML understands that nothing has changed between subsequent runs, so it re-uses the output of the last run (the outputs are persisted in the [artifact store](broken-reference/). This behavior is known as **caching**.

ZenML comes with caching enabled by default. Since ZenML automatically tracks and versions all inputs, outputs, and parameters of steps and pipelines, ZenML will not re-execute steps within the same pipeline on subsequent pipeline runs as long as there is no change in these three.

{% hint style="warning" %}
Currently, the caching does not automatically detect changes within the file system or on external APIs. Make sure to set caching to `False` on steps that depend on external inputs or if the step should run regardless of caching.
{% endhint %}

### Configuring caching behavior of your pipelines

Although caching is desirable in many circumstances, one might want to disable it in certain instances. For example, if you are quickly prototyping with changing step definitions or you have an external API state change in your function that ZenML does not detect.

There are multiple ways to take control of when and where caching is used:

#### Configuring caching for the entire pipeline

On a pipeline level, the caching policy can be set as a parameter within the `@pipeline` decorator as shown below:

```python
@pipeline(enable_cache=False)
def first_pipeline(....):
    """Pipeline with cache disabled"""
```

The setting above will disable caching for all steps in the pipeline, unless a step explicitly sets `enable_cache=True` (see below).

{% hint style="info" %}
When writing your pipelines, be explicit. This makes it clear when looking at the code if caching is enabled or disabled for any given pipeline.
{% endhint %}

#### Explicitly set `enable_cache` at the `@pipeline` level

Caching is enabled by default for ZenML Pipelines.

#### Configuring caching for individual steps

Caching can also be explicitly configured at a step level via a parameter of the `@step` decorator:

```python
@step(enable_cache=False)
def import_data_from_api(...):
    """Import most up-to-date data from public api"""
    ...
```

The code above turns caching off for this step only. This is very useful in practice since you might want to turn off caching for certain steps that take external input (like fetching data from an API or File IO) without affecting the overall pipeline caching behavior.

{% hint style="info" %}
You can get a graphical visualization of which steps were cached using the [ZenML Dashboard](broken-reference/).
{% endhint %}

#### Dynamically configuring caching for a pipeline run

Sometimes you want to have control over caching at runtime instead of defaulting to the hard-coded pipeline and step decorator settings. ZenML offers a way to override all caching settings at runtime:

```python
first_pipeline(step_1=..., step_2=...).run(enable_cache=False)
```

The code above disables caching for all steps of your pipeline, no matter what you have configured in the `@step` or `@parameter` decorators.
