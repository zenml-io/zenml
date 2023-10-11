---
description: Orchestrating the execution of ML pipelines.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Orchestrators

The orchestrator is an essential component in any MLOps stack as it is responsible for running your machine learning
pipelines. To do so, the orchestrator provides an environment that is set up to execute the steps of your pipeline. It
also makes sure that the steps of your pipeline only get executed once all their inputs (which are outputs of previous
steps of your pipeline) are available.

{% hint style="info" %}
Many of ZenML's remote orchestrators build [Docker](https://www.docker.com/) images in order to transport and execute
your pipeline code. If you want to learn more about how Docker images are built by ZenML, check
out [this guide](/docs/book/user-guide/advanced-guide/containerize-your-pipeline.md).
{% endhint %}

### When to use it

The orchestrator is a mandatory component in the ZenML stack. It is used to store all artifacts produced by pipeline
runs, and you are required to configure it in all of your stacks.

### Orchestrator Flavors

Out of the box, ZenML comes with a `local` orchestrator already part of the default stack that runs pipelines locally.
Additional orchestrators are provided by integrations:

| Orchestrator                                                                             | Flavor         | Integration  | Notes                                                                   |
| ---------------------------------------------------------------------------------------- | -------------- | ------------ | ----------------------------------------------------------------------- |
| [LocalOrchestrator](local.md)                                                            | `local`        | _built-in_   | Runs your pipelines locally.                                            |
| [LocalDockerOrchestrator](local-docker.md)                                               | `local_docker` | _built-in_   | Runs your pipelines locally using Docker.                               |
| [KubernetesOrchestrator](kubernetes.md)                                                  | `kubernetes`   | `kubernetes` | Runs your pipelines in Kubernetes clusters.                             |
| [KubeflowOrchestrator](kubeflow.md)                                                      | `kubeflow`     | `kubeflow`   | Runs your pipelines using Kubeflow.                                     |
| [VertexOrchestrator](vertex.md)                                                          | `vertex`       | `gcp`        | Runs your pipelines in Vertex AI.                                       |
| [SagemakerOrchestrator](sagemaker.md)                                                    | `sagemaker`    | `aws`        | Runs your pipelines in Sagemaker.                                       |
| [TektonOrchestrator](tekton.md)                                                          | `tekton`       | `tekton`     | Runs your pipelines using Tekton.                                       |
| [AirflowOrchestrator](airflow.md)                                                        | `airflow`      | `airflow`    | Runs your pipelines using Airflow.                                      |
| [GitHubActionsOrchestrator](../../../learning/component-gallery/orchestrators/github.md) | `github`       | `github`     | Runs your pipelines using GitHub Actions.                               |
| [Custom Implementation](custom.md)                                                       | _custom_       |              | Extend the orchestrator abstraction and provide your own implementation |

If you would like to see the available flavors of orchestrators, you can use the command:

```shell
zenml orchestrator flavor list
```

### How to use it

You don't need to directly interact with any ZenML orchestrator in your code. As long as the orchestrator that you want
to use is part of your active [ZenML stack](/docs/book/user-guide/starter-guide/understand-stacks.md), using the
orchestrator is as simple as executing a Python file
that [runs a ZenML pipeline](/docs/book/user-guide/starter-guide/starter-guide.md):

```shell
python file_that_runs_a_zenml_pipeline.py
```

#### Inspecting Runs in the Orchestrator UI

If your orchestrator comes with a separate user interface (for example Kubeflow, Airflow, Vertex), you can get the URL
to the orchestrator UI of a specific pipeline run using the following code snippet:

```python
from zenml.post_execution import get_run

pipeline_run = get_run("<PIPELINE_RUN_NAME>")
orchestrator_url = deployer_step.metadata["orchestrator_url"].value
```

#### Specifying per-step resources

If some of your steps require the orchestrator to execute them on specific hardware, you can specify them on your steps
as described [here](/docs/book/user-guide/advanced-guide/configure-steps-pipelines.md).

If your orchestrator of choice or the underlying hardware doesn't support this, you can also take a look
at [step operators](../step-operators/step-operators.md).
