---
description: Deploy pipelines to the public cloud.
---

# Guide for cloud-specific deployments

This guide will show how you can run the a pipeline in Kubeflow Pipelines deployed to a public cloud cluster. We will start with some pre-requisites and then move on to show the integration of your cloud provider's components with your ZenML stack. In addition to configuring the stack components in this guide, you can optionally run a pipeline step on a specialized cloud backend too. Check out the step operators [guide](../features/step-operators.md) for that!

## Pre-requisites

### Orchestrator

{% tabs %}
{% tab title="AWS" %}
* Have an existing AWS [EKS cluster](https://docs.aws.amazon.com/eks/latest/userguide/create-cluster.html) set up.
*   Download and [install](https://kubernetes.io/docs/tasks/tools/) `kubectl` and [configure](https://aws.amazon.com/premiumsupport/knowledge-center/eks-cluster-connection/) it to talk to your EKS cluster using the following command. Make sure you have the `aws` cli set up first.

    ```powershell
    aws eks --region REGION update-kubeconfig --name CLUSTER_NAME
    ```
* [Install](https://www.kubeflow.org/docs/components/pipelines/installation/standalone-deployment/#deploying-kubeflow-pipelines) Kubeflow Pipelines onto your cluster.
{% endtab %}

{% tab title="GCP" %}
* Have an existing GCP [GKE cluster](https://cloud.google.com/kubernetes-engine/docs/quickstart) set up.
*   Download and [install](https://kubernetes.io/docs/tasks/tools/) `kubectl` and [configure](https://cloud.google.com/kubernetes-engine/docs/how-to/cluster-access-for-kubectl) it to talk to your GKE cluster using the following command. Make sure you have the Google Cloud CLI set up first.

    ```powershell
    gcloud container clusters get-credentials CLUSTER_NAME
    ```
* [Install](https://www.kubeflow.org/docs/distributions/gke/deploy/overview/) Kubeflow Pipelines onto your cluster.
{% endtab %}

{% tab title="Azure" %}
* Have an existing [AKS cluster](https://azure.microsoft.com/en-in/services/kubernetes-service/#documentation) set up.
*   Download and [install](https://kubernetes.io/docs/tasks/tools/) `kubectl` and it to talk to your AKS cluster using the following command. Make sure you have the `az` cli set up first.

    ```powershell
    az aks get-credentials --resource-group RESOURCE_GROUP --name CLUSTER_NAME
    ```
* [Install](https://www.kubeflow.org/docs/components/pipelines/installation/standalone-deployment/#deploying-kubeflow-pipelines) Kubeflow Pipelines onto your cluster.

> Since Kubernetes v1.19, AKS has shifted to [`containerd`](https://docs.microsoft.com/en-us/azure/aks/cluster-configuration#container-runtime-configuration). However, the workflow controller installed with the Kubeflow installation has `Docker` set as the default runtime. In order to make your pipelines work, you have to change the value to one of the options listed [here](https://argoproj.github.io/argo-workflows/workflow-executors/#workflow-executors),  preferably `k8sapi`.&#x20;
>
> This change has to be made by editing the `containerRuntimeExecutor` property of the `ConfigMap` corresponding to the workflow controller. Run the following commands to first know what config map to change and then to edit it to reflect your new value.
>
> ```
> kubectl get configmap -n kubeflow
> kubectl edit configmap CONFIGMAP_NAME -n kubeflow
> # This opens up an editor that can be used to make the change.
> ```
{% endtab %}
{% endtabs %}

{% hint style="info" %}
If one or more of the deployments are not in the `Running` state, try increasing the number of nodes in your cluster.
{% endhint %}

{% hint style="warning" %}
If you are doing a manual install of the Kubeflow Pipelines, make sure that the service name for the ML pipeline is exactly `ml-pipeline` . This will ensure that ZenML can talk to your Kubeflow deployment.
{% endhint %}

### Container Registry

{% tabs %}
{% tab title="AWS" %}
* [Set up](https://docs.aws.amazon.com/AmazonECR/latest/userguide/get-set-up-for-amazon-ecr.html) an Elastic Container Registry (ECR) and create a repository (either public or private) with the name `zenml-kubeflow`. This is the repository to which ZenML will push your pipeline images.
* The path value to register with ZenML should be in the format `ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com`
* Authenticate your local `docker` CLI with your ECR registry using the following command. Replace the capitalized words with your values.

    ```powershell
    aws ecr get-login-password --region REGION | docker login --username aws --password-stdin ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com
    ```
{% endtab %}

{% tab title="GCP" %}
* Set up a [GCP Container Registry](https://cloud.google.com/container-registry/docs).
* [Authenticate](https://cloud.google.com/container-registry/docs/advanced-authentication) your local `docker` cli with your GCP container registry.
{% endtab %}

{% tab title="Azure" %}
* [Set up](https://azure.microsoft.com/en-in/services/container-registry/#get-started) an Azure Container Registry (ACR) and create a repository (either public or private) with the name `zenml-kubeflow` . This is the repository to which ZenML will push your pipeline images to.
*   Authenticate your local `docker` cli with your ACR registry using the following command.

    ```powershell
    az acr login --name REGISTRY_NAME
    ```
{% endtab %}
{% endtabs %}

### Artifact Store

{% tabs %}
{% tab title="AWS" %}

* [Create](https://docs.aws.amazon.com/AmazonS3/latest/userguide/create-bucket-overview.html) an Amazon S3 bucket in a region of your choice.
* Make sure that your EKS cluster is authorized to access the S3 bucket. This can be done in one of the following ways:
  * A simple way is to add an [`AmazonS3FullAccess`](https://console.aws.amazon.com/iam/home#/policies/arn:aws:iam::aws:policy/AmazonS3FullAccess) policy to your cluster node group's IAM role.
  * A complex way would be to create `ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_SESSION_TOKEN` environment variables in your EKS cluster. This can be done by extending the `zenmldocker/zenml` image and [adding](https://docs.docker.com/engine/reference/builder/#env) these variables in a Dockerfile. 
* The path for your bucket should be in this format `s3:\\your-bucket`.
{% endtab %}

{% tab title="GCP" %}
* [Create](https://cloud.google.com/storage/docs/creating-buckets) a GCP Cloud Storage Bucket in a region of your choice.
* Make sure that your GKE cluster is authorized to access the GCS bucket.
* The path for your bucket should be in this format `gs://your-bucket`.
{% endtab %}

{% tab title="Azure" %}
* [Create](https://docs.microsoft.com/en-us/azure/storage/common/storage-account-overview) an Azure Storage Account and [add](https://docs.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-portal) a _container_ to hold your _blobs._
* Open your storage account page on the Azure portal and follow these steps:
  * Keep the name of the storage account handy - it will be required in a later step.
  * From the navigation panel on the left, select **Access Keys** under **Security + networking**. Note any of the keys available there for future use.
* Make sure to set a combination of the following environment variables:`AZURE_STORAGE_CONNECTION_STRING` or `AZURE_STORAGE_ACCOUNT_NAME` and one of \[`AZURE_STORAGE_ACCOUNT_KEY`, `AZURE_STORAGE_SAS_TOKEN`]. \
  This can be done by extending the `zenmldocker/zenml` image and [adding](https://docs.docker.com/engine/reference/builder/#env) these variables in a Dockerfile.
* The path for your bucket should be in this format `az://<CONTAINER-NAME>`.
{% endtab %}
{% endtabs %}


## Integrating with ZenML

To run our pipeline on Kubeflow Pipelines deployed to cloud, we will create a new stack with these components that you have just created.

1. Install the cloud provider and the `kubeflow` plugin

    ```powershell
    zenml integration install <aws/gcp/azure>
    zenml integration install kubeflow
    ```

2. Register the stack components

    ```powershell
    zenml container-registry register cloud_registry --type=default --uri=$PATH_TO_YOUR_CONTAINER_REGISTRY
    zenml orchestrator register cloud_orchestrator --type=kubeflow --custom_docker_base_image_name=YOUR_IMAGE
    zenml metadata-store register kubeflow_metadata_store --type=kubeflow
    zenml artifact-store register cloud_artifact_store --type=<s3/gcp/azure> --path=$PATH_TO_YOUR_BUCKET

    # Register the cloud stack
    zenml stack register cloud_kubeflow_stack -m kubeflow_metadata_store -a cloud_artifact_store -o cloud_orchestrator -c cloud_registry
    ```
    
3. Activate the newly created stack.

    ```powershell
    zenml stack set cloud_kubeflow_stack
    ```

4. Do a pipeline run and check your Kubeflow UI to see it running there! 🚀

{% hint style="info" %}
* The **metadata store** stores metadata inside the Kubeflow Pipelines internal MySQL database.
* You can choose any name for your stack components apart from the ones used in the script above.
{% endhint %}

{% hint style="warning" %}
Make sure to replace `$PATH_TO_YOUR_BUCKET`and `$PATH_TO_YOUR_CONTAINER_REGISTRY` with the actual URI's of your bucket and container registry.
{% endhint %}
