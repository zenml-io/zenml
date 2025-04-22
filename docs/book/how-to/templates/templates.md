---
description: Create and run pipeline templates in ZenML to standardize execution.
icon: print
---

# Templates

In ZenML, pipeline templates (also known as "Run Templates") are pre-defined, parameterized configurations for your pipelines that can be easily executed from various interfaces - including the Python SDK, CLI, ZenML dashboard, or REST API. Think of them as blueprints for your pipeline runs, ready to be customized on the fly.

{% hint style="success" %}
Pipeline Templates are a [ZenML Pro](https://zenml.io/pro)-only feature. Please [sign up here](https://cloud.zenml.io) to get access.
{% endhint %}

![Working with Templates](../../.gitbook/assets/run-templates.gif)

## Understanding Pipeline Templates

While the simplest way to execute a ZenML pipeline is to directly call your pipeline function, pipeline templates offer several advantages for more complex workflows:

* **Standardization**: Ensure all pipeline runs follow a consistent configuration pattern
* **Parameterization**: Easily modify inputs and settings without changing code
* **Remote Execution**: Trigger pipelines through the dashboard or API without code access
* **Team Collaboration**: Share ready-to-use pipeline configurations with team members
* **Automation**: Integrate with CI/CD systems or other automated processes

Pipeline templates are particularly useful when working with remote stacks (having at least a remote orchestrator, artifact store, and container registry).

## Creating Pipeline Templates

You have several ways to create pipeline templates in ZenML:

### Using the Python SDK

You can create a template from an existing pipeline run:

```python
from zenml.client import Client

# Create from an existing run
run = Client().get_pipeline_run("<RUN_NAME_OR_ID>")
Client().create_run_template(
    name="<TEMPLATE_NAME>",
    deployment_id=run.deployment_id
)

# Or directly from a pipeline definition
from zenml import pipeline

@pipeline
def my_pipeline():
    ...

template = my_pipeline.create_run_template(name="<TEMPLATE_NAME>")
```

{% hint style="warning" %}
You need to select **a pipeline run that was executed on a remote stack** (i.e., at least a remote orchestrator, artifact store, and container registry) or have a remote stack active when creating the template.
{% endhint %}

### Using the CLI

You can create a template using the ZenML CLI:

```bash
# The <PIPELINE_SOURCE_PATH> will be `run.my_pipeline` if you defined a
# pipeline with name `my_pipeline` in a file called `run.py`
zenml pipeline create-run-template <PIPELINE_SOURCE_PATH> --name=<TEMPLATE_NAME>
```

{% hint style="warning" %}
You need to have an active **remote stack** while running this command or you can specify one with the `--stack` option.
{% endhint %}

### Using the Dashboard

To create a template through the ZenML dashboard:

1. Navigate to a pipeline run that was executed on a remote stack
2. Click on `+ New Template`
3. Enter a name for the template
4. Click `Create`

![Create Templates on the dashboard](../../.gitbook/assets/run-templates-create-1.png)

![Template Details](../../.gitbook/assets/run-templates-create-2.png)

## Running Pipeline Templates

Once you've created a template, you can run it through various interfaces:

### Using the Python SDK

Run a template programmatically:

```python
from zenml.client import Client

template = Client().get_run_template("<TEMPLATE_NAME>")
config = template.config_template

# [OPTIONAL] Modify the configuration if needed
config.steps["my_step"].parameters["my_param"] = new_value

# Trigger the pipeline with the template
Client().trigger_pipeline(
    template_id=template.id,
    run_configuration=config,
)
```

### Using the Dashboard

To run a template from the dashboard:

1. Either click `Run a Pipeline` on the main `Pipelines` page, or navigate to a specific template and click `Run Template`
2. On the `Run Details` page, you can:
   * Upload a `.yaml` configuration file
   * Modify the configuration using the built-in editor
3. Click `Run` to execute the template

![Run Details](../../.gitbook/assets/run-templates-run-1.png)

Once you run the template, a new run will be executed on the same stack as the original run.

### Using the REST API

To run a template through the REST API, you need to make a series of calls:

1. First, get the pipeline ID:

```bash
curl -X 'GET' \
  '<YOUR_ZENML_SERVER_URL>/api/v1/pipelines?hydrate=false&name=<PIPELINE_NAME>' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer <YOUR_TOKEN>'
```

2. Using the pipeline ID, get the template ID:

```bash
curl -X 'GET' \
  '<YOUR_ZENML_SERVER_URL>/api/v1/run_templates?hydrate=false&logical_operator=and&page=1&size=20&pipeline_id=<PIPELINE_ID>' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer <YOUR_TOKEN>'
```

3. Finally, trigger the pipeline with the template ID:

```bash
curl -X 'POST' \
  '<YOUR_ZENML_SERVER_URL>/api/v1/run_templates/<TEMPLATE_ID>/runs' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <YOUR_TOKEN>' \
  -d '{
  "steps": {"model_trainer": {"parameters": {"model_type": "rf"}}}
}'
```

{% hint style="info" %}
Learn how to get a bearer token for the curl commands [here](https://docs.zenml.io/pro/deployments/pro-api#programmatic-access-with-api-tokens).
{% endhint %}

## Advanced Usage: Running Templates from Other Pipelines

You can trigger templates from within other pipelines, enabling complex workflows:

```python
import pandas as pd

from zenml import pipeline, step
from zenml.artifacts.unmaterialized_artifact import UnmaterializedArtifact
from zenml.artifacts.utils import load_artifact
from zenml.client import Client
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration


@step
def trainer(data_artifact_id: str):
    df = load_artifact(data_artifact_id)


@pipeline
def training_pipeline():
    trainer()


@step
def load_data() -> pd.DataFrame:
    # Your data loading logic here
    return pd.DataFrame()


@step
def trigger_pipeline(df: UnmaterializedArtifact):
    # By using UnmaterializedArtifact we can get the ID of the artifact
    run_config = PipelineRunConfiguration(
        steps={"trainer": {"parameters": {"data_artifact_id": df.id}}}
    )

    Client().trigger_pipeline("training_pipeline", run_configuration=run_config)


@pipeline
def loads_data_and_triggers_training():
    df = load_data()
    trigger_pipeline(df)  # Will trigger the other pipeline
```

This pattern is useful for:

* Creating pipeline dependencies
* Implementing dynamic workflow orchestration
* Building multi-stage ML pipelines where different steps require different resources
* Separating data preparation from model training

Read more about:

* [PipelineRunConfiguration](https://sdkdocs.zenml.io/latest/core_code_docs/core-config.html#zenml.config.pipeline_run_configuration)
* [trigger\_pipeline API](https://sdkdocs.zenml.io/latest/core_code_docs/core-client.html#zenml.client.Client)
* [Unmaterialized Artifacts](https://docs.zenml.io/how-to/artifacts/complex_use_cases#unmaterialized-artifacts)

## Best Practices

1. **Use descriptive names** for your templates to make them easily identifiable
2. **Document template parameters** so other team members understand how to configure them
3. **Start with a working pipeline run** before creating a template to ensure it's properly configured
4. **Test templates with different configurations** to verify they work as expected
5. **Use version control** for your template configurations when storing them as YAML files
6. **Implement access controls** to manage who can run specific templates
7. **Monitor template usage** to understand how your team is using them

By using pipeline templates effectively, you can standardize ML workflows, improve team collaboration, and simplify the process of running pipelines in production environments.
