---
description: Interacting with your ZenML instance through the ZenML Client.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# 🐍 Python Client

Pipelines, runs, stacks, and many other ZenML resources are stored and versioned in a database within your ZenML instance behind the scenes. The ZenML Python `Client` allows you to fetch, update, or even create any of these resources programmatically in Python.

{% hint style="info" %}
In all other programming languages and environments, you can interact with ZenML resources through the REST API endpoints of your ZenML server instead. Checkout the `/docs/` page of your server for an overview of all available endpoints.
{% endhint %}

### Usage Example

The following example shows how to use the ZenML Client to fetch the last 10 pipeline runs that you ran yourself on the stack that you have currently set:

```python
from zenml.client import Client

client = Client()

my_runs_on_current_stack = client.list_pipeline_runs(
    stack_id=client.active_stack_model.id,  # on current stack
    user_id=client.active_user.id,  # ran by you
    sort_by="desc:start_time",  # last 10
    size=10,
)

for pipeline_run in my_runs_on_current_stack:
    print(pipeline_run.name)
```

### List of Resources

These are the main ZenML resources that you can interact with via the ZenML Client:

#### Pipelines, Runs, Artifacts

* **Pipelines**: The pipeline (versions) that were implicitly tracked when running ZenML pipelines.
* **Pipeline Runs**: Information about all pipeline runs that were executed on your ZenML instance.
* **Step Runs**: The steps of all pipeline runs. Mainly useful for directly fetching a specific step of a run by its ID.
* **Artifacts**: Information about all artifacts that were written to your artifact stores as part of pipeline runs.
* **Schedules**: Metadata about the schedules that you have used to [schedule pipeline runs](../how-to/build-pipelines/schedule-a-pipeline.md).
* **Builds**: The pipeline-specific Docker images that were created when [containerizing your pipeline](../how-to/customize-docker-builds/README.md).
* **Code Repositories**: The git code repositories that you have connected with your ZenML instance. See [here](../user-guide/production-guide/connect-code-repository.md) for more information.

{% hint style="info" %}
Checkout the [documentation on fetching runs](../how-to/build-pipelines/fetching-pipelines.md) for more information on the various ways how you can fetch and use the pipeline, pipeline run, step run, and artifact resources in code.
{% endhint %}

#### Stacks, Infrastructure, Authentication

* **Stack**: The stacks registered in your ZenML instance.
* **Stack Components**: The stack components registered in your ZenML instance, e.g., all orchestrators, artifact stores, model deployers, ...
* **Flavors**: The [stack component flavors](../getting-started/core-concepts.md#flavor) available to you, including:
  * Built-in flavors like the [local orchestrator](../component-guide/orchestrators/local.md),
  * Integration-enabled flavors like the [Kubeflow orchestrator](../component-guide/orchestrators/kubeflow.md),
  * Custom flavors that you have [created yourself](../how-to/stack-deployment/implement-a-custom-stack-component.md).
* **User**: The users registered in your ZenML instance. If you are running locally, there will only be a single `default` user.
* **Secrets**: The infrastructure authentication secrets that you have registered in the [ZenML Secret Store](../how-to/interact-with-secrets.md).
* **Service Connectors**: The service connectors that you have set up to [connect ZenML to your infrastructure](../how-to/auth-management/README.md).

### Client Methods

#### Reading and Writing Resources

**List Methods**

Get a list of resources, e.g.:

```python
client.list_pipeline_runs(
    stack_id=client.active_stack_model.id,  # filter by stack
    user_id=client.active_user.id,  # filter by user
    sort_by="desc:start_time",  # sort by start time descending
    size=10,  # limit page size to 10
)
```

These methods always return a [Page](https://sdkdocs.zenml.io/latest/core\_code\_docs/core-models/#zenml.models.page\_model) of resources, which behaves like a standard Python list and contains, by default, the first 50 results. You can modify the page size by passing the `size` argument or fetch a subsequent page by passing the `page` argument to the list method.

You can further restrict your search by passing additional arguments that will be used to filter the results. E.g., most resources have a `user_id` associated with them that can be set to only list resources created by that specific user. The available filter argument options are different for each list method; check out the method declaration in the [Client SDK documentation](https://sdkdocs.zenml.io/latest/core\_code\_docs/core-client/) to find out which exact arguments are supported or have a look at the fields of the corresponding filter model class.

Except for pipeline runs, all other resources will by default be ordered by creation time ascending. E.g., `client.list_artifacts()` would return the first 50 artifacts ever created. You can change the ordering by specifying the `sort_by` argument when calling list methods.

**Get Methods**

Fetch a specific instance of a resource by either resource ID, name, or name prefix, e.g.:

```python
client.get_pipeline_run("413cfb42-a52c-4bf1-a2fd-78af2f7f0101")  # ID
client.get_pipeline_run("first_pipeline-2023_06_20-16_20_13_274466")  # Name
client.get_pipeline_run("first_pipeline-2023_06_20-16")  # Name prefix
```

**Create, Update, and Delete Methods**

Methods for creating / updating / deleting resources are only available for some of the resources and the required arguments are different for each resource. Checkout the [Client SDK Documentation](https://sdkdocs.zenml.io/latest/core\_code\_docs/core-client/) to find out whether a specific resource supports write operations through the Client and which arguments are required.

#### Active User and Active Stack

For some use cases you might need to know information about the user that you are authenticated as or the stack that you have currently set as active. You can fetch this information via the `client.active_user` and `client.active_stack_model` properties respectively, e.g.:

```python
my_runs_on_current_stack = client.list_pipeline_runs(
    stack_id=client.active_stack_model.id,  # on current stack
    user_id=client.active_user.id,  # ran by you
)
```

### Resource Models

The methods of the ZenML Client all return **Response Models**, which are [Pydantic Models](https://docs.pydantic.dev/latest/usage/models/) that allow ZenML to validate that the returned data always has the correct attributes and types. E.g., the `client.list_pipeline_runs` method always returns type `Page[PipelineRunResponseModel]`.

{% hint style="info" %}
You can think of these models as similar to types in strictly-typed languages, or as the requirements of a single endpoint in an API. In particular, they are **not related to machine learning models** like decision trees, neural networks, etc.
{% endhint %}

ZenML also has similar models that define which information is required to create, update, or search resources, named **Request Models**, **Update Models**, and **Filter Models** respectively. However, these models are only used for the server API endpoints, and not for the Client methods.

{% hint style="info" %}
To find out which fields a specific resource model contains, checkout the [ZenML Models SDK Documentation](https://sdkdocs.zenml.io/latest/core\_code\_docs/core-models/#zenml.models) and expand the source code to see a list of all fields of the respective model. Note that all resources have **Base Models** that define fields that response, request, update, and filter models have in common, so you need to take a look at the base model source code as well.
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
