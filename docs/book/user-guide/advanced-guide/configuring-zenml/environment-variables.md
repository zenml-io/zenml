---
description: How to control ZenML behavior with environmental variables.
---

# ZenML Environment Variables

There are a few pre-defined environmental variables that can be used to control 
the behavior of ZenML. See the list below with default values and options:

## Logging verbosity

```bash
export ZENML_LOGGING_VERBOSITY=INFO
```

Choose from `INFO`, `WARN`, `ERROR`, `CRITICAL`, `DEBUG`.

## Disable step logs

Usually, ZenML [stores step logs in the artifact store](../pipelining-features/managing-steps.md#enable-or-disable-logs-storing),
but this can sometimes cause performance bottlenecks, especially if the code utilizes
progress bars.

If you want to configure whether logged output from steps is stored or not, set
the `ZENML_DISABLE_STEP_LOGS_STORAGE` environment variable to `true`. Note that
this will mean that logs from your steps will no longer be stored and thus won't
be visible on the dashboard any more.

```bash
export ZENML_DISABLE_STEP_LOGS_STORAGE=false
```

## ZenML repository path

To configure where ZenML will install and look for its repository, set the
environment variable `ZENML_REPOSITORY_PATH`.

```bash
export ZENML_REPOSITORY_PATH=/path/to/somewhere
```

## Analytics

Please see [our full page](../../../user-guide/advanced-guide/configuring-zenml/global-settings-of-zenml.md#usage-analytics) on what analytics are tracked and how you can opt-out,
but the quick summary is that you can set this to `false` if you want to opt out
of analytics.

```bash
export ZENML_ANALYTICS_OPT_IN=false
```

## Debug mode

Setting to `true` switches to developer mode:

```bash
export ZENML_DEBUG=true
```

## Active stack

Setting the `ZENML_ACTIVE_STACK_ID` to a specific UUID will make the 
corresponding stack the active stack:
```bash
export ZENML_ACTIVE_STACK_ID=<UUID-OF-YOUR-STACK>
```

## Prevent pipeline execution

When `true`, this prevents a pipeline from executing:
```bash
export ZENML_PREVENT_PIPELINE_EXECUTION=false
```

## Disable rich traceback

Set to `false` to disable the [`rich` traceback](https://rich.readthedocs.io/en/stable/traceback.html):


```bash
export ZENML_ENABLE_RICH_TRACEBACK=true
```

## ZenML global config path

To set the path to the global config file, used by ZenML to manage and store the
state for a number of settings, set the environment variable as follows:

```bash
export ZENML_CONFIG_PATH=/path/to/somewhere
```

## Server configuration

For more information on server configuration, see the [ZenML Server documentation](../../../deploying-zenml/zenml-self-hosted/deploy-with-docker.md)
for more, especially the section entitled "ZenML server configuration options".


## Client configuration

Setting the `ZENML_STORE_URL` and `ZENML_STORE_API_KEY` environment
variables automatically connects your ZenML Client to the specified server. This method
is particularly useful when you are using the ZenML client in an automated CI/CD
workload environment like GitHub Actions or GitLab CI or in a containerized
environment like Docker or Kubernetes:

```bash
export ZENML_STORE_URL=https://...
export ZENML_STORE_API_KEY=<API_KEY>
```

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>