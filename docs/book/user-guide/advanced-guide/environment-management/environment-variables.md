---
description: How to control ZenML behavior with environmental variables.
---

# Environment Variables

There are a few pre-defined environmental variables that can be used to control the behavior of ZenML. See the list below with default values and options:

## Logging verbosity

```bash
export ZENML_LOGGING_VERBOSITY=INFO
```

Choose from `INFO`, `WARN`, `ERROR`, `CRITICAL`, `DEBUG`.

If you want to configure whether logged output from steps is stored or not, set the `ZENML_DISABLE_STEP_LOGS_STORAGE` environment variable to `true`. Note that this will mean that logs from your steps will no longer be stored and thus won't be visible on the dashboard any more.

## ZenML repository path

To configure where ZenML will install and look for its repository, set the environment variable `ZENML_REPOSITORY_PATH`.

```bash
export ZENML_REPOSITORY_PATH=/path/to/somewhere
```

## Analytics

Please see [our full page](global-settings-of-zenml.md#usage-analytics) on what analytics are tracked and how you can opt-out, but the quick summary is that you can set this to `false` if you want to opt out of analytics.

```bash
export ZENML_ANALYTICS_OPT_IN=true
```

## Debug mode

Setting to `true` switches to developer mode:

```bash
ZENML_DEBUG=false
```

## Active stack

Setting the `ZENML_ACTIVE_STACK_ID` to a specific UUID will make the corresponding stack the active stack:

```bash
ZENML_ACTIVE_STACK_ID=<UUID-OF-YOUR-STACK>
```

## Prevent pipeline execution

When `true`, this prevents a pipeline from executing:

```bash
ZENML_PREVENT_PIPELINE_EXECUTION=false
```

## Disable rich traceback

Set to `false` to disable the [`rich` traceback](https://rich.readthedocs.io/en/stable/traceback.html):

```bash
ZENML_ENABLE_RICH_TRACEBACK=true
```

## ZenML global config path

To set the path to the global config file, used by ZenML to manage and store the state for a number of settings, set the environment variable as follows:

```bash
export ZENML_CONFIG_PATH=/path/to/somewhere
```

## Integration logs

Setting this to `false` disables integrations logs suppression:

```bash
export ZENML_SUPPRESS_LOGS=false
```

## Server configuration

For more information on server configuration, see the [ZenML Server documentation](../../../deploying-zenml/zenml-self-hosted/deploy-with-docker.md) for more, especially the section entitled "ZenML server configuration options".
