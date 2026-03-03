---
description: Configuring environment variables.
icon: globe
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Environment variables

Environment variables can be configured to be available at runtime during step execution. ZenML provides two ways to set environment variables:

1. **Plain text environment variables**: Configure key-value pairs directly
2. **Secrets as environment variables**: Use ZenML secrets where the secret values become environment variables. Check out [this page](../secrets/secrets.md) for more information on secret management in ZenML.

{% hint style="info" %}
If you need environment variables to be available at image built time, check out the [containerization documentation](../containerization/containerization.md#environment-variables) for more information.
{% endhint %}

## Configuration levels

Environment variables and secrets can be configured at different levels with increasing precedence:

1. **Stack components** - Available for all pipelines executed on stacks containing this component
2. **Stack** - Available for all pipelines executed on this stack
3. **Pipeline** - Available for all steps in this pipeline
4. **Step** - Available only for this specific step

{% hint style="info" %}
**Precedence order**: Step configuration overrides pipeline configuration, which overrides stack configuration, which overrides stack component configuration. Additionally, secrets always take precedence over direct environment variables when both are configured with the same key.
{% endhint %}

## Automatic environment variable injection

When executing a pipeline, ZenML automatically scans your local environment for any variables that start with the `__ZENML__` prefix and adds them to the pipeline environment. The prefix is removed during this process.

For example, if you set:
```bash
export __ZENML__MY_VAR=my_value
```

It will be available in your steps as follows:
```python
import os
from zenml import step

@step
def my_step():
    my_var = os.environ["MY_VAR"]  # "my_value"
```

## Configuring environment variables on stack components

Configure environment variables and secrets that will be available for all pipelines executed on stacks containing this component.

{% tabs %}
{% tab title="CLI" %}
```bash
# Configure environment variables
zenml orchestrator update <ORCHESTRATOR_NAME> --env <KEY>=<VALUE>
# Remove environment variables (set empty value)
zenml orchestrator update <ORCHESTRATOR_NAME> --env <KEY>=

# Attach secrets (secret values become environment variables)
zenml orchestrator update <ORCHESTRATOR_NAME> --secret <SECRET_NAME_OR_ID>
# Remove secrets
zenml orchestrator update <ORCHESTRATOR_NAME> --remove-secret <SECRET_NAME_OR_ID>
```
{% endtab %}

{% tab title="Python" %}
```python
from zenml import Client

Client().update_stack_component(
    name_id_or_prefix=<COMPONENT_NAME_OR_ID>,
    component_type=<COMPONENT_TYPE>,
    environment={
        "<KEY>": "<VALUE>",
        # Set to `None` to remove from previously configured environment
        "<KEY>": None
    },
    add_secrets=["<SECRET_NAME_OR_ID>", "<SECRET_NAME_OR_ID>"],
    remove_secrets=["<SECRET_NAME_OR_ID>"]
)
```
{% endtab %}
{% endtabs %}

## Setting environment variables on stacks

Configure environment variables and secrets for all pipelines executed on this stack.

{% tabs %}
{% tab title="CLI" %}
```bash
# Configure environment variables
zenml stack update <STACK_NAME> --env <KEY>=<VALUE>
# Remove environment variables
zenml stack update <STACK_NAME> --env <KEY>=

# Attach secrets
zenml stack update <STACK_NAME> --secret <SECRET_NAME_OR_ID>
# Remove secrets
zenml stack update <STACK_NAME> --remove-secret <SECRET_NAME_OR_ID>
```
{% endtab %}

{% tab title="Python" %}
```python
from zenml import Client

Client().update_stack(
    name_id_or_prefix=<STACK_NAME_OR_ID>,
    environment={
        "<KEY>": "<VALUE>",
        # Set to `None` to remove from previously configured environment
        "<KEY>": None
    },
    add_secrets=["<SECRET_NAME_OR_ID>"],
    remove_secrets=["<SECRET_NAME_OR_ID>"]
)
```
{% endtab %}
{% endtabs %}

## Configuring environment variables on pipelines

Configure environment variables and secrets for all steps of a pipeline. See [this page](../steps-pipelines/configuration.md) for more details on how to configure pipelines.

```python
from zenml import pipeline

# On the decorator
@pipeline(
    environment={
        "<KEY>": "<VALUE>",
        "<KEY>": "<VALUE>"
    },
    secrets=["<SECRET_NAME_OR_ID>", "<SECRET_NAME_OR_ID>"]
)
def my_pipeline():
    ...

# Using the `with_options(...)` method
my_pipeline = my_pipeline.with_options(
    environment={
        "<KEY>": "<VALUE>",
        "<KEY>": "<VALUE>"
    },
    secrets=["<SECRET_NAME_OR_ID>", "<SECRET_NAME_OR_ID>"]
)
```

## Setting environment variables on steps

Configure environment variables and secrets for individual steps. See [this page](../steps-pipelines/configuration.md) for more details on how to configure steps.

```python
from zenml import step

# On the decorator
@step(
    environment={
        "<KEY>": "<VALUE>",
        "<KEY>": "<VALUE>"
    },
    secrets=["<SECRET_NAME_OR_ID>"]
)
def my_step() -> str:
    ...

# Using the `with_options(...)` method
my_step = my_step.with_options(
    environment={
        "<KEY>": "<VALUE>",
        "<KEY>": "<VALUE>"
    },
    secrets=["<SECRET_NAME_OR_ID>", "<SECRET_NAME_OR_ID>"]
)
```

## When environment variables are set

The timing of when environment variables are set depends on the orchestrator being used:

- The [Databricks](../../component-guide/orchestrators/databricks.md) and [Lightning](../../component-guide/orchestrators/lightning.md) orchestrators will set the environment variables right before your step code is being executed
- **All other orchestrators** set environment variables already at container startup time

{% hint style="info" %}
**Environment variables from secrets** are always set right before your step code is being executed for security reasons, regardless of the orchestrator.
{% endhint %}
