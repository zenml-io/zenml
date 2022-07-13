---
description: Orchestrate Machine Learning pipelines
---

## When to use it

## Orchestrator Flavors


| Orchestrator         | Flavor    | Integration    | Notes |
|----------------------------|-----------|----------------|-------------|
| [LocalOrchestrator](./local.md)   | `local`   | _built-in_     | Runs your pipelines locally. |
| [KubernetesOrchestrator](./kubernetes.md) | `kubernetes` | `kubernetes`     | Runs your pipelines in Kubernetes clusters. |
| [KubeflowOrchestrator](./kubeflow.md)       | `kubeflow`       | `kubeflow`    | Runs your pipelines using Kubeflow. |
| [VertexOrchestrator](./gcloud_vertexai.md)     | `vertex`     | `gcp`     | Runs your pipelines in Vertex AI. |
| [AirflowOrchestrator](./airflow.md)    | `airflow`    | `airflow`     | Runs your pipelines locally using Airflow. |
| [GitHubActionsOrchestrator](./github_actions.md)    | `github`    | `github`     | Runs your pipelines using GitHub Actions. |

If you would like to see the available flavors of orchestrators, you can 
use the command:

```shell
zenml orchestrator flavor list
```

<!-- The orchestrator is one of the most critical components of your stack, as it
defines where the actual pipeline job runs. It controls how and where each
individual step within a pipeline is executed. Therefore, the orchestrator can
be used to great effect to scale jobs into production. -->


<!-- # Run your Pipeline on Kubeflow

[Kubeflow Pipelines](https://www.kubeflow.org/docs/components/pipelines/introduction/) is a pipeline orchestrator built for machine learning workflows. When developing ML models, you probably develop [your pipelines](../extending-zenml/getting-started.md#pipeline) on your local machine initially as this allows for quicker iteration and debugging. However, at a certain point when you are finished with its design, you might want to transition to a more production-ready setting and deploy the pipeline to a more robust environment.

You can watch a tutorial video of an example that uses a Kubeflow Pipelines stack [here](https://www.youtube.com/watch?v=b5TXRYkdL3w):

{% embed url="https://www.youtube.com/watch?v=b5TXRYkdL3w" %}

Or you can also check out our example of this [here](https://github.com/zenml-io/zenml/tree/main/examples/kubeflow_pipelines_orchestration) .

You could also pull it into your local environment like this:

```shell
zenml example pull kubeflow_pipelines_orchestration
```

If you don't want to manually set things up, feel free to run it with this command:

```shell
zenml example run kubeflow_pipelines_orchestration
```

### Pre-requisites

In order to run go from basic orchestration to using Kubeflow, we have to install a few tools that allow ZenML to spin up a local Kubeflow Pipelines setup:

* [K3D](https://k3d.io/v5.2.1/#installation) to spin up a local Kubernetes cluster
* The Kubernetes command-line tool [Kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl) to deploy Kubeflow Pipelines
* [Docker](https://docs.docker.com/get-docker/) to build Docker images that run your pipeline in Kubernetes pods

{% hint style="warning" %}
The local Kubeflow Pipelines deployment requires more than 2 GB of RAM, so if you're using Docker Desktop make sure to update the resource limits in the preferences.
{% endhint %}

### Installation

Next, we will install all packages that are required for ZenML to run on Kubeflow Pipelines:

```bash
zenml integration install kubeflow
```

### Create a local Kubeflow Pipelines Stack

A [Stack](../core-concepts.md#stack) is the configuration of the
surrounding infrastructure where ZenML pipelines
are run and managed. For now, a `Stack` consists of:

* [A metadata store](../core-concepts.md#metadata-store): To store
  metadata like parameters and artifact URIs.
* [An artifact store](../core-concepts.md#artifact-store): To store
  interim data which is returned from steps.
* [An orchestrator](../core-concepts.md#orchestrator): A service
  that actually kicks off and runs each step of the pipeline.
* An
  optional [container registry](../core-concepts.md#container-registry):
  To store Docker images that are created to run your pipeline.

When you did `zenml init` at the start of this guide, a default `local_stack` was created with local versions of all of these. In order to see the stack you can check it out in the command line:

```bash
zenml stack list
```

Output:

```
┏━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME           │ ARTIFACT_STORE │ METADATA_STORE │ ORCHESTRATOR         │ CONTAINER_REGISTRY │ MODEL_DEPLOYER ┃
┠────────┼──────────────────────┼────────────────┼────────────────┼──────────────────────┼────────────────────┼────────────────┨
┃   👉   │ default              │ default        │ default        │ default              │                    │                ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```

![Your local stack when you start.](../assets/localstack.png)

Let's stick with the default metadata and artifact stores for now and create a stack with a Kubeflow orchestrator and a default local container registry:

```bash
# Make sure to create the local registry on port 5000 for it to work 
zenml container-registry register local_registry --flavor=default --uri=localhost:5000 
zenml orchestrator register kubeflow_orchestrator --flavor=kubeflow
zenml stack register local_kubeflow_stack \
    -m default \
    -a default \
    -o kubeflow_orchestrator \
    -c local_registry

# Activate the newly-created stack
zenml stack set local_kubeflow_stack
```

Output:

```bash
Container registry `local_registry` successfully registered!
Orchestrator `kubeflow_orchestrator` successfully registered!
Stack `local_kubeflow_stack` successfully registered!
Active stack: local_kubeflow_stack
```

![Your stack with a Kubeflow Pipelines Orchestrator](../assets/localstack-with-kubeflow-orchestrator.png)

{% hint style="warning" %}
In a real-world production setting we would also switch to something like a MySQL-based metadata store and an Azure-, GCP-, or S3-based artifact store. We have just skipped that part to keep everything in one machine to make it a bit easier to run this guide.
{% endhint %}

### Start up Kubeflow Pipelines locally

ZenML takes care of setting up and configuring the local Kubeflow Pipelines deployment. All we need to do is run:

```bash
zenml stack up
```

When the setup is finished, you should see a local URL which you can access in your browser and take a look at the Kubeflow Pipelines UI. (Note: depending on your hardware and computer, this could take a few minutes to run to completion.)

### Run the pipeline

There is one minor change we need to make to run a pipeline: we need to specify the Python package requirements that ZenML should install inside the Docker image it creates for you. We do that by passing a file path as a parameter to the `@pipeline` decorator:

```python
@pipeline(requirements="path_to_requirements.txt")
def mnist_pipeline(...)
```

Additionally, you might also want to define a `.dockerignore` to make sure only relevant parts of your project are added to the Docker images that are used for Kubeflow Pipelines. Make sure to not add the `.zen` folder to the `.dockerignore`.

```python
@pipeline(requirements="path_to_requirements.txt",
          dockerignore_file="path_to_dockerignore")
def mnist_pipeline(...)
```

We can now run the pipeline by executing the Python script:

```bash
python run.py
```

Even though the pipeline script is essentially the same, the output will be a lot different from last time. ZenML will detect that `local_kubeflow_stack` is the active stack, and do the following:

* Build a Docker image containing all the necessary Python packages and files
* Push the Docker image to the local container registry
* Schedule a pipeline run in Kubeflow Pipelines

Once the script is finished, you should be able to see the pipeline run at this local URL: [http://localhost:8080/#/runs](http://localhost:8080/#/runs).

### Clean up

Once you're done experimenting, you can delete the local Kubeflow cluster and all associated resources by calling:

```bash
zenml stack down --force
```

### Run the same pipeline on Kubeflow Pipelines deployed to the cloud

You can now run the same pipeline in Kubeflow Pipelines deployed to a cluster on the cloud. Refer to the Cloud Pipelines Deployment Guide [here](execute-pipelines-in-cloud.md) to know more and follow along!

## Conclusion

If you made it this far, congratulations! You're one step closer to being production-ready with your ML workflows! Here is what we achieved in this entire guide:

* Experimented locally and built-up an ML pipeline.
* Transitioned to production by deploying a continuously training pipeline on newly arriving data.
* All the while retained complete lineage and tracking over parameters, data, code, and metadata.

### Keep going!

There are lot's more things you do in production that you might consider adding to your workflows:

* Adding a step
  to [automatically deploy the models](../extending-zenml/model-deployers.md) to
  a REST endpoint.
* Setting
  up [a drift detection and validation step](perform-drift-detection.md)
  to test models before deploying.
* [Using a secrets manager](manage-your-secrets.md) to store secret keys
  for use in your pipelines.

ZenML will help with all of these and more. Check out our other guides to learn more! -->
