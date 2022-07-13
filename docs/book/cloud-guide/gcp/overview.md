---
description: Setting up your stack on Google Cloud Platform (GCP)
---

GCP is one of the most popular cloud providers and offers a range of services that can be used while building your MLOps stacks. You can learn more about machine learning at GCP on their [website](https://cloud.google.com/solutions/ai).

# Available Stack Components

This is a list of all supported GCP services that you can use as ZenML stack components.
## Google Kubernetes Engine (GKE)

Google Kubernetes Engine (GKE) provides a managed environment for deploying, managing, and scaling your containerized applications using Google infrastructure. The GKE environment consists of multiple machines (specifically, Compute Engine instances) grouped together to form a cluster. [Learn more here](https://cloud.google.com/kubernetes-engine/docs/concepts/kubernetes-engine-overview).


* An GKE cluster can be used to run multiple **orchestrators**.
    * [A Kubernetes-native orchestrator.](../../mlops_stacks/orchestrators/kubernetes.md)
    * [A Kubeflow orchestrator.](../../mlops_stacks/orchestrators/kubeflow.md)
* You can host **model deployers** on the cluster.
    * [A Seldon model deployer.](../../mlops_stacks/model_deployers/seldon.md)
    * [An MLflow model deployer.](../../mlops_stacks/model_deployers/mlflow.md)
* Experiment trackers can also be hosted on the cluster.
    * [An MLflow experiment tracker](../../mlops_stacks/experiment_trackers/mlflow.md)

## Cloud Storage Bucket (GCS)

Cloud Storage is a service for storing your objects in Google Cloud. An object is an immutable piece of data consisting of a file of any format. You store objects in containers called buckets. [Learn more here](https://cloud.google.com/storage/docs/introduction).

* You can use a [GCS bucket as an artifact store](../../mlops_stacks/artifact_stores/gcloud_gcs.md) to hold files from our pipeline runs like models, data and more. 

## Google Container Registry (GCR)

Container Registry is a service for storing private container images. It is being deprecated in favour of Artifact Registry, support for which will be coming soon to ZenML!

* A [GCR registry can be used as a container registry](../../mlops_stacks/container_registries/gcloud_gcr.md) stack component to host images of your pipelines. 

## Vertex AI

Vertex AI brings together the Google Cloud services for building ML under one, unified UI and API. In Vertex AI, you can now train and compare models using AutoML or custom code training and all your models are stored in one central model repository. [Learn more here](https://cloud.google.com/vertex-ai).

* You can use [Vertex AI as a step operator](../../mlops_stacks/step_operators/gcloud_vertexai.md) to run specific steps from your pipeline using it as the backend.

* [Vertex AI can also be used as an orchestrator](../../mlops_stacks/orchestrators/gcloud_vertexai.md) for your pipelines.

## CloudSQL

Cloud SQL is a fully-managed database service that helps you set up, maintain, manage, and administer your relational databases on Google Cloud Platform.
You can use Cloud SQL with a MySQL server in ZenML. [Learn more here](https://cloud.google.com/sql/docs).

* You can use a [CloudSQL MySQL instance as a metadata store](../../mlops_stacks/metadata_stores/mysql.md) to track metadata from your pipeline runs.

## Secret Manager

Secret Manager is a secure and convenient storage system for API keys, passwords, certificates, and other sensitive data. Secret Manager provides a central place and single source of truth to manage, access, and audit secrets across Google Cloud. [Learn more here](https://cloud.google.com/secret-manager/docs).

* You can store your secrets to be used inside a pipeline by registering the [Google Secret Manager as a ZenML secret manager](../../mlops_stacks/secrets_managers/gcloud.md) stack component.

In the following pages, you will find step-by-step guides for setting up some common stacks using the GCP console and the CLI. More combinations and components are progressively updated in the form of new pages.
