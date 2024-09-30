---
description: How to control ZenML behavior with environmental variables.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# 🌎 Environment Variables

There are a few pre-defined environmental variables that can be used to control the behavior of ZenML. See the list below with default values and options:

## Logging verbosity

```bash
export ZENML_LOGGING_VERBOSITY=INFO
```

Choose from `INFO`, `WARN`, `ERROR`, `CRITICAL`, `DEBUG`.

## Disable step logs

Usually, ZenML [stores step logs in the artifact store](../how-to/control-logging/enable-or-disable-logs-storing.md), but this can sometimes cause performance bottlenecks, especially if the code utilizes progress bars.

If you want to configure whether logged output from steps is stored or not, set the `ZENML_DISABLE_STEP_LOGS_STORAGE` environment variable to `true`. Note that this will mean that logs from your steps will no longer be stored and thus won't be visible on the dashboard anymore.

```bash
export ZENML_DISABLE_STEP_LOGS_STORAGE=false
```

## ZenML repository path

To configure where ZenML will install and look for its repository, set the environment variable `ZENML_REPOSITORY_PATH`.

```bash
export ZENML_REPOSITORY_PATH=/path/to/somewhere
```

## Analytics

Please see [our full page](global-settings.md#usage-analytics) on what analytics are tracked and how you can opt out, but the quick summary is that you can set this to `false` if you want to opt out of analytics.

```bash
export ZENML_ANALYTICS_OPT_IN=false
```

## Debug mode

Setting to `true` switches to developer mode:

```bash
export ZENML_DEBUG=true
```

## Active stack

Setting the `ZENML_ACTIVE_STACK_ID` to a specific UUID will make the corresponding stack the active stack:

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

## Disable colorful logging

If you wish to disable colorful logging, set the following environment variable:

```bash
ZENML_LOGGING_COLORS_DISABLED=true
```

Note that setting this on the [client environment](../how-to/configure-python-environments/README.md#client-environment-or-the-runner-environment) (e.g. your local machine which runs the pipeline) will automatically disable colorful logging on remote orchestrators. If you wish to disable it locally, but turn on for remote orchestrators, you can set the `ZENML_LOGGING_COLORS_DISABLED` environment variable in your orchestrator's environment as follows:

```python
docker_settings = DockerSettings(environment={"ZENML_LOGGING_COLORS_DISABLED": "false"})

# Either add it to the decorator
@pipeline(settings={"docker": docker_settings})
def my_pipeline() -> None:
    my_step()

# Or configure the pipelines options
my_pipeline = my_pipeline.with_options(
    settings={"docker": docker_settings}
)
```

## ZenML global config path

To set the path to the global config file, used by ZenML to manage and store the state for a number of settings, set the environment variable as follows:

```bash
export ZENML_CONFIG_PATH=/path/to/somewhere
```

## Server configuration

For more information on server configuration, see the [ZenML Server documentation](../getting-started/deploying-zenml/deploy-with-docker.md#zenml-server-configuration-options) for more, especially the section entitled "ZenML server configuration options".

## Client configuration

Setting the `ZENML_STORE_URL` and `ZENML_STORE_API_KEY` environment variables automatically connects your ZenML Client to the specified server. This method is particularly useful when you are using the ZenML client in an automated CI/CD workload environment like GitHub Actions or GitLab CI or in a containerized environment like Docker or Kubernetes:

```bash
export ZENML_STORE_URL=https://...
export ZENML_STORE_API_KEY=<API_KEY>
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
