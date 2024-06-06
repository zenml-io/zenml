---
description: A guide to debug common issues and get help.
---

# 🐞 Debug and solve issues

If you stumbled upon this page, chances are you're facing issues with using ZenML. This page documents suggestions and best practices to let you debug, get help, and solve issues quickly.

### When to get help?

We suggest going through the following checklist before asking for help:

*   Search on Slack using the built-in Slack search function at the top of the page.

    ![Searching on Slack.](../.gitbook/assets/slack\_search\_bar.png)
* Search on [GitHub issues](https://github.com/zenml-io/zenml/issues).
*   Search the [docs](https://docs.zenml.io) using the search bar in the top right corner of the page.

    ![Searching on docs page.](../.gitbook/assets/doc\_search\_bar.png)
* Check out the [common errors](debug-and-solve-issues.md#most-common-errors) section below.
* Understand the problem by studying the [additional logs](debug-and-solve-issues.md#41-additional-logs) and [client/server logs](debug-and-solve-issues.md#client-and-server-logs).

Chances are you'd find your answers there. If you can't find any clue, then it's time to post your question on [Slack](https://zenml.io/slack).

### How to post on Slack?

When posting on Slack it's useful to provide the following information (when applicable) so that we get a complete picture before jumping into solutions.

#### 1. System Information

Let us know relevant information about your system. We recommend running the following in your terminal and attaching the output to your question.

```shell
zenml info -a -s
```

You can optionally include information about specific packages where you're having problems by using the `-p` option. For example, if you're having problems with the `tensorflow` package, you can run:

```shell
zenml info -p tensorflow
```

The output should look something like this:

```yaml
ZENML_LOCAL_VERSION: 0.40.2
ZENML_SERVER_VERSION: 0.40.2
ZENML_SERVER_DATABASE: mysql
ZENML_SERVER_DEPLOYMENT_TYPE: alpha
ZENML_CONFIG_DIR: /Users/my_username/Library/Application Support/zenml
ZENML_LOCAL_STORE_DIR: /Users/my_username/Library/Application Support/zenml/local_stores
ZENML_SERVER_URL: https://someserver.zenml.io
ZENML_ACTIVE_REPOSITORY_ROOT: /Users/my_username/coding/zenml/repos/zenml
PYTHON_VERSION: 3.9.13
ENVIRONMENT: native
SYSTEM_INFO: {'os': 'mac', 'mac_version': '13.2'}
ACTIVE_WORKSPACE: default
ACTIVE_STACK: default
ACTIVE_USER: some_user
TELEMETRY_STATUS: disabled
ANALYTICS_CLIENT_ID: xxxxxxx-xxxxxxx-xxxxxxx
ANALYTICS_USER_ID: xxxxxxx-xxxxxxx-xxxxxxx
ANALYTICS_SERVER_ID: xxxxxxx-xxxxxxx-xxxxxxx
INTEGRATIONS: ['airflow', 'aws', 'azure', 'dash', 'evidently', 'facets', 'feast', 'gcp', 'github',
'graphviz', 'huggingface', 'kaniko', 'kubeflow', 'kubernetes', 'lightgbm', 'mlflow',
'neptune', 'neural_prophet', 'pillow', 'plotly', 'pytorch', 'pytorch_lightning', 's3', 'scipy',
'sklearn', 'slack', 'spark', 'tensorboard', 'tensorflow', 'vault', 'wandb', 'whylogs', 'xgboost']
```

System information provides more context to your issue and also eliminates the need for anyone to ask when they're trying to help. This increases the chances of your question getting answered and saves everyone's time.

#### 2. What happened?

Tell us briefly:

* What were you trying to achieve?
* What did you expect to happen?
* What actually happened?

#### 3. How to reproduce the error?

Walk us through how to reproduce the same error you had step-by-step, whenever possible. Use the format you prefer. Write it in text or record a video, whichever lets you get the issue at hand across to us!

#### 4. Relevant log output

As a general rule of thumb, always attach relevant log outputs and the full
error traceback to help us understand what happened under the hood. If the full
error traceback does not fit into a text message, attach a file or use a service
like [Pastebin](https://pastebin.com/) or [Github's Gist](https://gist.github.com/).

Along with the error traceback, we recommend to always share the output of the following commands:

* `zenml status`
* `zenml stack describe`

When applicable, also attach logs of the orchestrator. For example, if you're using the Kubeflow orchestrator, include the logs of the pod that was running the step that failed.

Usually, the default log you see in your terminal is sufficient, in the event it's not, then it's useful to provide additional logs. Additional logs are not shown by default, you'll have to toggle an environment variable for it. Read the next section to find out how.

**4.1 Additional logs**

When the default logs are not helpful, ambiguous, or do not point you to the root of the issue, you can toggle the value of the `ZENML_LOGGING_VERBOSITY` environment variable to change the type of logs shown. The default value of `ZENML_LOGGING_VERBOSITY` environment variable is:

```
ZENML_LOGGING_VERBOSITY=INFO
```

You can pick other values such as `WARN`, `ERROR`, `CRITICAL`, `DEBUG` to change what's shown in the logs. And export the environment variable in your terminal. For example in Linux:

```shell
export ZENML_LOGGING_VERBOSITY=DEBUG
```

Read more about how to set environment variables for:

* For [Linux](https://linuxize.com/post/how-to-set-and-list-environment-variables-in-linux/).
* For [macOS](https://youngstone89.medium.com/setting-up-environment-variables-in-mac-os-28e5941c771c).
* For [Windows](https://www.computerhope.com/issues/ch000549.htm).

### Client and server logs

When facing a ZenML Server-related issue, you can view the logs of the server to introspect deeper. To achieve this, run:

```shell
zenml logs
```

The logs from a healthy server should look something like this:

```shell
INFO:asyncio:Syncing pipeline runs...
2022-10-19 09:09:18,195 - zenml.zen_stores.metadata_store - DEBUG - Fetched 4 steps for pipeline run '13'. (metadata_store.py:315)
2022-10-19 09:09:18,359 - zenml.zen_stores.metadata_store - DEBUG - Fetched 0 inputs and 4 outputs for step 'importer'. (metadata_store.py:427)
2022-10-19 09:09:18,461 - zenml.zen_stores.metadata_store - DEBUG - Fetched 0 inputs and 4 outputs for step 'importer'. (metadata_store.py:427)
2022-10-19 09:09:18,516 - zenml.zen_stores.metadata_store - DEBUG - Fetched 2 inputs and 2 outputs for step 'normalizer'. (metadata_store.py:427)
2022-10-19 09:09:18,606 - zenml.zen_stores.metadata_store - DEBUG - Fetched 0 inputs and 4 outputs for step 'importer'. (metadata_store.py:427)
```

### Most common errors

This section documents frequently encountered errors among users and solutions to each.

#### Error initializing rest store

Typically, the error presents itself as:

```bash
RuntimeError: Error initializing rest store with URL 'http://127.0.0.1:8237': HTTPConnectionPool(host='127.0.0.1', port=8237): Max retries exceeded with url: /api/v1/login (Caused by 
NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f9abb198550>: Failed to establish a new connection: [Errno 61] Connection refused'))
```

If you restarted your machine after deploying ZenML then you have to run `zenml up` again after each restart. Local ZenML deployments don't survive machine restarts.

#### Column 'step\_configuration' cannot be null

```bash
sqlalchemy.exc.IntegrityError: (pymysql.err.IntegrityError) (1048, "Column 'step_configuration' cannot be null")
```

This happens when a step configuration is too long. We changed the limit from 4K to 65K chars, but it could still happen if you have excessively long strings in your config.

#### 'NoneType' object has no attribute 'name'

This is also a common error you might encounter when you do not have the necessary stack components registered on the stack. For example:

```shell
╭─────────────────────────────── Traceback (most recent call last) ────────────────────────────────╮
│ /home/dnth/Documents/zenml-projects/nba-pipeline/run_pipeline.py:24 in <module>                  │
│                                                                                                  │
│    21 │   reference_data_splitter,                                                               │
│    22 │   TrainingSplitConfig,                                                                   │
│    23 )                                                                                          │
│ ❱  24 from steps.trainer import random_forest_trainer                                            │
│    25 from steps.encoder import encode_columns_and_clean                                         │
│    26 from steps.importer import (                                                               │
│    27 │   import_season_schedule,                                                                │
│                                                                                                  │
│ /home/dnth/Documents/zenml-projects/nba-pipeline/steps/trainer.py:24 in <module>                 │
│                                                                                                  │
│   21 │   max_depth: int = 10000                                                                  │
│   22 │   target_col: str = "FG3M"                                                                │
│   23                                                                                             │
│ ❱ 24 @step(enable_cache=False, experiment_tracker=experiment_tracker.name)                       │
│   25 def random_forest_trainer(                                                                  │
│   26 │   train_df_x: pd.DataFrame,                                                               │
│   27 │   train_df_y: pd.DataFrame,                                                               │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
AttributeError: 'NoneType' object has no attribute 'name'
```

In the above error snippet, the `step` on line 24 expects an experiment tracker but could not find it on the stack. To solve it, register an experiment tracker of your choice on the stack. For instance:

```shell
zenml experiment-tracker register mlflow_tracker --flavor=mlflow
```

and update your stack with the experiment tracker:

```shell
zenml stack update -e mlflow_tracker
```

This also applies to all other [stack components](../component-guide/README.md).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
