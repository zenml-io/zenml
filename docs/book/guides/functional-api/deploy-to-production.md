---
description: Deploy pipelines to production
---

# Deploy to production

If you want to see the code for this chapter of the guide, head over to the [GitHub](https://github.com/zenml-io/zenml/tree/main/examples/low\_level\_guide/chapter\_7.py).

You can also watch a tutorial video of a Kubeflow stack based example [here](https://www.youtube.com/watch?v=b5TXRYkdL3w).

## Deploy pipelines to production

When developing ML models, you probably develop your pipelines on your local machine initially as this allows for quicker iteration and debugging. However, at a certain point when you are finished with its design, you might want to transition to a more production-ready setting and deploy the pipeline to a more robust environment.

### Pre-requisites

In order to run this example, we have to install a few tools that allow ZenML to spin up a local Kubeflow Pipelines setup:

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

A [Stack](../../introduction/core-concepts.md) is the configuration of the surrounding infrastructure where ZenML pipelines are run and managed. For now, a `Stack` consists of:

* A metadata store: To store metadata like parameters and artifact URIs
* An artifact store: To store interim data step output.
* An orchestrator: A service that actually kicks off and runs each step of the pipeline.
* An optional container registry: To store Docker images that are created to run your pipeline.

When you did `zenml init` at the start of this guide, a default `local_stack` was created with local version of all of these. In order to see the stack you can check it out in the command line:

```bash
zenml stack list
```

Output:

```bash
STACKS:
key                   stack_type    metadata_store_name    artifact_store_name    orchestrator_name      container_registry_name
--------------------  ------------  ---------------------  ---------------------  ---------------------  -------------------------
local_stack           base          local_metadata_store   local_artifact_store   local_orchestrator
```

![Your local stack when you start.](../../assets/localstack.png)

Let's stick with the `local_metadata_store` and a `local_artifact_store` for now and create a stack with a Kubeflow orchestrator and a local container registry

```bash
# Make sure to create the local registry on port 5000 for it to work 
zenml container-registry register local_registry --type=default --uri=localhost:5000 
zenml orchestrator register kubeflow_orchestrator --type=kubeflow
zenml stack register local_kubeflow_stack \
    -m local_metadata_store \
    -a local_artifact_store \
    -o kubeflow_orchestrator \
    -c local_registry

# Activate the newly created stack
zenml stack set local_kubeflow_stack
```

Output:

```bash
Container registry `local_registry` successfully registered!
Orchestrator `kubeflow_orchestrator` successfully registered!
Stack `local_kubeflow_stack` successfully registered!
Active stack: local_kubeflow_stack
```

![Your stack with a Kubeflow Pipelines Orchestrator](../../assets/localstack-with-kubeflow-orchestrator.png)

{% hint style="warning" %}
In the real world we would also switch to something like a MySQL-based metadata store and an Azure-, GCP-, or S3-based artifact store. We have just skipped that part to keep everything in one machine to make it a bit easier to run this guide.
{% endhint %}

### Start up Kubeflow Pipelines locally

ZenML takes care of setting up and configuring the local Kubeflow Pipelines deployment. All we need to do is run:

```bash
zenml stack up
```

When the setup is finished, you should see a local URL which you can access in your browser and take a look at the Kubeflow Pipelines UI.

### Run the pipeline

There is one minor change we need to make to run the pipeline from the previous chapter: we need to specify the Python package requirements that ZenML should install inside the Docker image it creates for you. We do that by passing a file path as a parameter to the `@pipeline` decorator:

```python
@pipeline(requirements_file="path_to_requirements.txt")
def mnist_pipeline(...)
```

Additionally, you might also want to define a `.dockerignore` to make sure only relevant parts of your
project are added to the docker images that are used for kubeflow pipelines. Make sure to not add the `.zen` 
folder to the dockerignore.

```python
@pipeline(requirements_file="path_to_requirements.txt", dockerignore_file="path_to_dockerignore")
def mnist_pipeline(...)
```

We can now run the pipeline by simply executing the Python script:

```bash
python chapter_7.py
```

Even though the pipeline script is essentially the same, the output will be a lot different from last time. ZenML will detect that `local_kubeflow_stack` is the active stack, and do the following:

* Build a docker image containing all the necessary python packages and files
* Push the docker image to the local container registry
* Schedule a pipeline run in Kubeflow Pipelines

Once the script is finished, you should be able to see the pipeline run [here](http://localhost:8080/#/runs).

### Clean up

Once you're done experimenting, you can delete the local Kubernetes cluster and all associated resources by calling:

```bash
zenml stack down
```

### Run the same pipeline on Kubeflow Pipelines deployed to the cloud

We will now run the same pipeline in Kubeflow Pipelines deployed to a cluster on the cloud. 
Refer to the Cloud Pipelines Deployment Guide [here](../../features/guide-aws-gcp-azure.md) to know more and follow along!

## Conclusion

If you made it this far, congratulations! You're one step closer to being production-ready with your ML workflows! Here is what we achieved in this entire guide:

* Experimented locally and built-up a ML pipeline.
* Transitioned to production by deploying a continuously training pipeline on newly arriving data.
* All the while retained complete lineage and tracking over parameters, data, code, and metadata.

### Coming soon

There are lot's more things you do in production that you might consider adding to your workflows:

* Adding a step to automatically deploy the models to a REST endpoint.
* Setting up a drift detection and validation step to test models before deploying.
* Creating a batch inference pipeline to get predictions.

ZenML will help with all of these and above -> Watch out for future releases and the next extension of this guide coming soon!
