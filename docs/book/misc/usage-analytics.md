# Usage Analytics

To help us better understand how the community uses ZenML, the pip package reports _anonymized_ usage statistics. You can always opt-out by using the CLI command:

```bash
zenml config analytics opt-out
```

```text
Currently, opting in and out of analytics is a global setting applicable to all ZenML repositories within your system.
```

## Why ZenML collects analytics <a id="motivation"></a>

In addition to the community at large, ZenML is created and maintained by a startup based in Munich, Germany called [maiot GmbH](https://maiot.io). We're a team of techies that love MLOps and want to build tools that fellow developers would love to use in their daily work. [This is us](https://maiot.io/team/), if you want to put faces to the names!

However, in order to improve ZenML and understand how it is being used, we need to use analytics to have an overview of how its used 'in the wild'. This not only helps us find bugs, but also helps us prioritize features and commands that might be useful in future releases. If we did not have this information, all we really get is pip download statistics and chatting with people directly, which while being valuable, is not enough to seriously better the tool as a whole.

## How ZenML collects these statistics <a id="implementation"></a>

ZenML uses [`Segment`](https://segment.com/) as the data aggregation library for all our analytics. The entire code is entirely visible and can be seen at [`zenml_analytics.py`](https://github.com/maiot-io/zenml/blob/main/zenml/utils/zenml_analytics.py). The main function is the [`track`](https://github.com/maiot-io/zenml/blob/main/zenml/utils/zenml_analytics.py#L167) function that triggers a [Segment Analytics Track event](https://segment.com/docs/connections/spec/track/), which runs on a separate background thread from the main thread.

None of the data sent can identify you individually, but allows us to understand how ZenML is bring used holistically.

## What does ZenML collect? <a id="what"></a>

ZenML triggers an asynchronous [Segment Track Event](https://segment.com/docs/connections/spec/track/) on the following events, which is also viewable in the [`zenml_analytics.py`](https://github.com/maiot-io/zenml/blob/main/zenml/utils/zenml_analytics.py) file in the GitHub repository.

```python
# Datasources

GET_DATASOURCES = "Datasources listed"

CREATE_DATASOURCE = "Datasource created"

# Functions

CREATE_STEP = "Step created"

GET_STEPS_VERSIONS = "Step Versions listed"

GET_STEP_VERSION = "Step listed"

# Pipelines

CREATE_PIPELINE = "Pipeline created"

REGISTER_PIPELINE = "Pipeline registered"

RUN_PIPELINE = "Pipeline run"

GET_PIPELINES = "Pipelines fetched"

GET_PIPELINE_ARTIFACTS = "Pipeline Artifacts fetched"

# Repo

CREATE_REPO = "Repository created"

INITIALIZE = "ZenML initialized"
```

In addition, each Segment Track event collects the following metadata:

* A unique UUID that is anonymous.
* The ZenML version.
* Operating system information, e.g. Ubuntu Linux 16.04

