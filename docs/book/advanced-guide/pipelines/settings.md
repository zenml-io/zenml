---
description: Configuring pipelines, steps, and stack components in ZenML.
---

# Settings in ZenML

## Video Tutorial

{% embed url="https://www.youtube.com/embed/hI-UNV7uoNI" %} Configuring pipelines, steps, and stack components in ZenML {% endembed %}

This video gives an overview of everything discussed in this chapter,
especially with a focus on the [post ZenML 0.20.0](../../guidelines/migration-zero-twenty.md) world!

## Settings in ZenML

As discussed in a [previous chapter](../../starter-guide/pipelines/iterating.md), there are two ways to configure anything in ZenML:

- `BaseParameters`: Runtime configuration passed down as a parameter to step functions.
- `BaseSettings`: Runtime settings passed down to stack components and pipelines.

We have [already discussed `BaseParameters`](../../starter-guide/pipelines/iterating.md) and now is the time to talk about its brother, `BaseSettings`.

### What can be configured?

Looked at one way, `BaseParameters` configure steps within a pipeline to behave in a different way during runtime. But what other
things can be configured at runtime? Here is a list:

- Controlling general step behavior like [enabling or disabling cache](../../starter-guide/pipelines/iterating.md) or how outputs are [materialized](../pipelines/materializers.md).
- The [resources](./step-resources.md) of a step.
- Configuring the [containerization](./containerization.md) process of a pipeline (e.g. What requirements get installed in the Docker image).
- Stack component specific configuration, e.g., if you have an experiment tracker passing in the name of the experiment at runtime.

You will learn about all of the above in more detail later, but for now,
lets try to understand that all of this configuration flows through one central concept, called `BaseSettings` (From here on, we use `settings` and `BaseSettings` as analagous in this guide).

### How to use settings

#### Method 1: Directly on the decorator

The most basic way to set settings is through the `settings` variable
that exists in both `@step` and `@pipeline` decorators:

```python
@step(settings=...)
  ...

@pipeline(settings=...)
```

{% hint style="info" %}
Once you set settings on a pipeline, they will be applied to all steps with some exception. See the [later section on precendence for more details](#heirarchy-and-precendence).
{% endhint %}

In this case, `settings` can be passed as a simple dict, where the `keys` are one of the following:



#### Method 2: On the step/pipeline instance

step_instance/pipeline_instance.configure(…): Configures the instance -> will be set for all runs using the instance

#### Method 3: Configuring with YAML

Generate a template for a config file: `pipeline_instance.write_run_configuration_template(path=<PATH>)`

### The `extra` dict

You might have noticed another dict that is available to pass through to steps and pipelines called `extra`. This dict is meant to be used to pass
any configuration down to the pipeline, step, or stack components that the user has use of.

An example of this is if I want to tag a pipeline, I can do the following:

```python
@pipeline(name='my_pipeline', extra={'tag': 'production'})
  ...
```

This tag is now associated and tracked with all pipeline runs, and can be fetched later with the [post-execution workflow](../../starter-guide/pipelines/fetching-pipelines.md):

```python
from zenml.post_execution import get_pipeline

p = get_pipeline('my_pipeline')

# print out the extra
print(p.runs[-1].pipeline_configuration['extra'])
# {'tag': 'production'}
```

### Heirarchy and precendence

Some settings can be configured on pipelines and steps, some only on one of the two. Pipeline level settings will be automatically applied to all steps, but if the same setting is configured on a step as well that takes precedence. Merging similar to the example below.

### Merging settings on class/instance/run:

Merging settings on class/instance/run:

when a settings object is configured, ZenML merges the values with previously configured keys. E.g.:

```python
from zenml.config import ResourceSettings

@step(settings={"resources": ResourceSettings(cpu_count=2, memory="1GB")})
def my_step() -> None:
  ...

step_instance = my_step()
step_instance.configure(settings={"resources": ResourceSettings(gpu_count=1, memory="2GB")})
step_instance.configuration.settings["resources"] # cpu_count: 2, gpu_count=1, memory="2GB"
```

In the above example, the two settings were merged into one automatically.
