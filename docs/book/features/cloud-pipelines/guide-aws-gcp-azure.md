---
description: Deploy pipelines to public cloud
---

# Guide for cloud-specific deployments

This guide will show how you can run the a pipeline in Kubeflow Pipelines deployed to a public cloud cluster. We will start with some pre-requisites and then move on to show the integration of your cloud provider's components with your ZenML stack.


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

### Step Operators

{% tabs %}
{% tab title="AzureML" %}
* First, you require a `Machine learning` [resource on Azure](https://docs.microsoft.com/en-us/azure/machine-learning/quickstart-create-resources). 
If you don't already have one, you can create it through the `All resources` 
page on the Azure portal. 
* Once your resource is created, you can head over to the `Azure Machine 
Learning Studio` and [create a compute cluster](https://docs.microsoft.com/en-us/azure/machine-learning/quickstart-create-resources#cluster) 
to run your pipelines. 
* Next, you will need an `environment` for your pipelines. You can simply 
create one following the guide [here](https://docs.microsoft.com/en-us/azure/machine-learning/how-to-manage-environments-in-studio).
* Finally, we have to set up our artifact store. In order to do this, we need 
to [create a blob container](https://docs.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-portal)
on Azure. 

Optionally, you can also create a [Service Principal for authentication](https://docs.microsoft.com/en-us/azure/developer/java/sdk/identity-service-principal-auth). 
This might especially be useful if you are planning to orchestrate your 
pipelines in a non-local setup such as Kubeflow where your local authentication 
won't be accessible.

The command to register the stack component would like the following.

```bash
zenml step-operator register azureml \
    --type=azureml \
    --subscription_id=<AZURE_SUBSCRIPTION_ID> \
    --resource_group=<AZURE_RESOURCE_GROUP> \
    --workspace_name=<AZURE_WORKSPACE_NAME> \
    --compute_target_name=<AZURE_COMPUTE_TARGET_NAME> \
    --environment_name=<AZURE_ENVIRONMENT_NAME> 
```

{% endtab %}

{% tab title="Amazon SageMaker" %}
* First, you need to create a role in the IAM console that you want the jobs running in Sagemaker to assume. This role should at least have the `AmazonS3FullAccess` and `AmazonSageMakerFullAccess` policies applied. Check [this link](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-roles.html#sagemaker-roles-create-execution-role) to learn how to create a role.

* Next, you need to choose what instance type needs to be used to run your jobs. You can get the list [here](https://docs.aws.amazon.com/sagemaker/latest/dg/notebooks-available-instance-types.html).

* Optionally, you can choose an S3 bucket to which Sagemaker should output any artifacts from your training run. 

* You can also supply an experiment name if you have one created already. Check [this guide](https://docs.aws.amazon.com/sagemaker/latest/dg/experiments-create.html) to know how. If not provided, the job runs would be independent.

* You can also choose a custom docker image that you want ZenML to use as a base image for creating an environment to run your jobs in Sagemaker. 

* You need to have the `aws` cli set up with the right credentials. Make sure you have the permissions to create and manage Sagemaker runs. 

* A container registry has to be configured in the stack. This registry will be used by ZenML to push your job images that Sagemaker will run. Check out the [cloud guide](https://docs.zenml.io/features/cloud-pipelines/guide-aws-gcp-azure) to learn how you can set up an elastic container registry. 

Once you have all these values handy, you can proceed to setting up the components required for your stack.

The command to register the stack component would like the following.

```bash
zenml step-operator register sagemaker \
    --type=sagemaker
    --role=<SAGEMAKER_ROLE> \
    --instance_type=<SAGEMAKER_INSTANCE_TYPE>
    --base_image=<CUSTOM_BASE_IMAGE>
    --bucket_name=<S3_BUCKET_NAME>
    --experiment_name=<SAGEMAKER_EXPERIMENT_NAME>
```

{% endtab %}

Once registered and activated, it can be used for a step by simply adding the `custom_step_operator` parameter to the step decorator.

```python
@step(custom_step_operator="some_step_operator")
def step_with_step_operator():
	pass
```



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
    zenml step-operator register ...

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
