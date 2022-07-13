---
description: Setting up your stack on Microsoft Azure
---

Azure is one of the most popular cloud providers and offers a range of services that can be used while building your MLOps stacks. You can learn more about machine learning at Azure on their [website](https://azure.microsoft.com/en-in/services/machine-learning/).

# Available Stack Components

This is a list of all supported Azure services that you can use as ZenML stack components.
## Azure Kubernetes Service (AKS)

Azure Kubernetes Service (AKS) is a managed Kubernetes service with hardened security and fast delivery.It allows you to quickly deploy a production ready Kubernetes cluster in Azure. [Learn more here](https://docs.microsoft.com/en-us/azure/aks/).


* An AKS cluster can be used to run multiple **orchestrators**.
    * [A Kubernetes-native orchestrator.](../../mlops_stacks/orchestrators/kubernetes.md)
    * [A Kubeflow orchestrator.](../../mlops_stacks/orchestrators/kubeflow.md)
* You can host **model deployers** on the cluster.
    * [A Seldon model deployer.](../../mlops_stacks/model_deployers/seldon.md)
    * [An MLflow model deployer.](../../mlops_stacks/model_deployers/mlflow.md)
* Experiment trackers can also be hosted on the cluster.
    * [An MLflow experiment tracker](../../mlops_stacks/experiment_trackers/mlflow.md)

## Azure Blob Storage

Azure Blob storage is Microsoft's object storage solution for the cloud. Blob storage is optimized for storing massive amounts of unstructured data. Blob storage offers three types of resources: the storage account, a container in the storage account and a blob in a container. [Learn more here](https://docs.microsoft.com/en-us/azure/storage/blobs/storage-blobs-introduction).

* You can use an [Azure Blob Storage Container as an artifact store](../../mlops_stacks/artifact_stores/azure_blob_storage.md) to hold files from our pipeline runs like models, data and more. 

## Azure Container Registry

Azure Container Registry is a managed registry service based on the open-source Docker Registry 2.0. Create and maintain Azure container registries to store and manage your container images and related artifacts. [Learn more here](https://docs.microsoft.com/en-us/azure/container-registry/container-registry-intro).

* An [Azure container registry can be used as a ZenML container registry](../../mlops_stacks/container_registries/azure.md) stack component to host images of your pipelines. 

## AzureML

Azure Machine Learning is a cloud service for accelerating and managing the machine learning project lifecycle. Machine learning professionals, data scientists, and engineers can use it in their day-to-day workflows to train and deploy models, and manage MLOps. [Learn more here](https://docs.microsoft.com/en-us/azure/machine-learning/overview-what-is-azure-machine-learning).

* You can use [AzureML compute as a step operator](../../mlops_stacks/step_operators/azureml.md) to run specific steps from your pipeline using it as the backend.

## Azure SQL server

The Azure SQL metadata service is not yet supported because ZenML doesn't yet support a matching Azure secrets manager.

## Key Vault

ZenML doesn't support the key vault secret manager by Azure yet. The integration is coming soon and contributions are welcome!

In the following pages, you will find step-by-step guides for setting up some common stacks using the Azure console and the CLI. More combinations and components are progressively updated in the form of new pages.
