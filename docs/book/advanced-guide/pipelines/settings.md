---
description: Configuring pipelines, steps, and stack components in ZenML.
---

# Settings in ZenML

## Video Tutorial

{% embed url="https://www.youtube.com/embed/hI-UNV7uoNI" %}

This video gives an overview of everything discussed in this chapter,
especially with a focus on the [post ZenML 0.20.0](../../guidelines/migration-zero-twenty.md) world!

## Settings in ZenML

As discussed in a [previous chapter](../../starter-guide/pipelines/iterating.md), there are two ways to configure anything in ZenML:

- `BaseParameters`: Runtime configuration passed down as a parameter to step functions.
- `BaseSettings`: Runtime settings passed down to stack components and pipelines.

We have [already discussed `BaseParameters`](../../starter-guide/pipelines/iterating.md) and now is the time to talk about its brother, `BaseSettings`.

We can further break down settings into two groups:

- General settings that can be used on all ZenML pipelines: `DockerSettings` and `ResourceSettings`.
- Stack component specific settings: these can be used to supply runtime configurations to certain stack components (key= <COMPONENT_TYPE>.<COMPONENT_FLAVOR>). Settings for components not in the active stack will be ignored

### Configuring with YAML

Generate a template for a config file: `pipeline_instance.write_run_configuration_template(path=<PATH>)`

### Heirarchy and precendence

Some settings can be configured on pipelines and steps, some only on one of the two. Pipeline level settings will be automatically applied to all steps, but if the same setting is configured on a step as well that takes precedence. Merging similar to the example above

step_instance/pipeline_instance.configure(…): Configures the instance -> will be set for all runs using the instance

pipeline.run(…): allows configuration in code or using a yaml file. Configurations in code overwrite settings in the file

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