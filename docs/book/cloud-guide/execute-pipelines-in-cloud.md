---
description: Deploy pipelines to the public cloud.
---

# Guide for cloud-specific deployments

This guide will show how you can run your pipelines in Kubeflow Pipelines 
deployed to a public cloud cluster. We will start with some prerequisites and 
then move on to show the integration of your cloud provider's components with 
your ZenML stack. In addition to configuring the stack components in this guide,
you can optionally run a pipeline step on a specialized cloud backend too. 
Check out the step operators [guide](run-steps-on-specialized-hardware.md) for that!

{% hint style="info" %}
We have recently also added a Vertex AI orchestrator to our arsenal of
orchestrators (thanks @Gabriel Martin). So if you are running on GCP and want to
try out a serverless alternative to Kubeflow, check out our example on how to
run the Vertex AI Orchestrator 
[here](https://github.com/zenml-io/zenml/tree/main/examples/vertex_ai_orchestration).
{% endhint %}

## Pre-requisites

### Orchestrator

{% tabs %}
{% tab title="AWS" %}

* Have an existing
  AWS [EKS cluster](https://docs.aws.amazon.com/eks/latest/userguide/create-cluster.html)
  set up.
* Make sure you have the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) set up.
* Download and [install](https://kubernetes.io/docs/tasks/tools/) `kubectl`
  and [configure](https://aws.amazon.com/premiumsupport/knowledge-center/eks-cluster-connection/)
  it to talk to your EKS cluster using the following command:

  ```powershell
  aws eks --region REGION update-kubeconfig --name CLUSTER_NAME
  ```
* [Install](https://www.kubeflow.org/docs/components/pipelines/installation/standalone-deployment/#deploying-kubeflow-pipelines)
  Kubeflow Pipelines onto your cluster.
  {% endtab %}

{% tab title="GCP" %}

* Have an existing
  GCP [GKE cluster](https://cloud.google.com/kubernetes-engine/docs/quickstart)
  set up.
* Make sure you have the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install-sdk) set up first.
* Download and [install](https://kubernetes.io/docs/tasks/tools/) `kubectl`
  and [configure](https://cloud.google.com/kubernetes-engine/docs/how-to/cluster-access-for-kubectl)
  it to talk to your GKE cluster using the following command:

  ```powershell
  gcloud container clusters get-credentials CLUSTER_NAME
  ```
* [Install](https://www.kubeflow.org/docs/distributions/gke/deploy/overview/)
  Kubeflow Pipelines onto your cluster.
  {% endtab %}

{% tab title="Azure" %}

* Have an
  existing [AKS cluster](https://azure.microsoft.com/en-in/services/kubernetes-service/#documentation)
  set up.
* Make sure you have the [`az` CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) set up first.
* Download and [install](https://kubernetes.io/docs/tasks/tools/) `kubectl` and
  it to talk to your AKS cluster using the following command:

  ```powershell
  az aks get-credentials --resource-group RESOURCE_GROUP --name CLUSTER_NAME
  ```
* [Install](https://www.kubeflow.org/docs/components/pipelines/installation/standalone-deployment/#deploying-kubeflow-pipelines)
  Kubeflow Pipelines onto your cluster.

> Since Kubernetes v1.19, AKS has shifted
>
to [`containerd`](https://docs.microsoft.com/en-us/azure/aks/cluster-configuration#container-runtime-configuration)
> . However, the workflow controller installed with the Kubeflow installation
> has `Docker` set as the default runtime. In order to make your pipelines work,
> you have to change the value to one of the options
>
listed [here](https://argoproj.github.io/argo-workflows/workflow-executors/#workflow-executors)
> , preferably `k8sapi`.&#x20;
>
> This change has to be made by editing the `containerRuntimeExecutor` property
> of the `ConfigMap` corresponding to the workflow controller. Run the following
> commands to first know what config map to change and then to edit it to
> reflect
> your new value.
>
> ```
> kubectl get configmap -n kubeflow
> kubectl edit configmap CONFIGMAP_NAME -n kubeflow
> # This opens up an editor that can be used to make the change.
> ```
{% endtab %}
{% endtabs %}

{% hint style="info" %}
If one or more of the deployments are not in the `Running` state, try increasing
the number of nodes in your cluster.
{% endhint %}

{% hint style="warning" %}
If you're installing Kubeflow Pipelines manually, make sure the Kubernetes 
service is called exactly `ml-pipeline`. This is a requirement for ZenML to 
connect to your Kubeflow Pipelines deployment.
{% endhint %}

### Container Registry

{% tabs %}
{% tab title="AWS" %}

* [Set up](https://docs.aws.amazon.com/AmazonECR/latest/userguide/get-set-up-for-amazon-ecr.html)
  an Elastic Container Registry (ECR) and create a repository (either public or
  private) with the name `zenml-kubeflow`. This is the repository to which ZenML
  will push your pipeline images.
* The path value to register with ZenML should be in the
  format `ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com`
* Authenticate your local `docker` CLI with your ECR registry using the
  following command. Replace the capitalized words with your values.

    ```powershell
    aws ecr get-login-password --region REGION | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com
    ```

{% endtab %}

{% tab title="GCP" %}

* Set up
  a [GCP Container Registry](https://cloud.google.com/container-registry/docs).
* [Authenticate](https://cloud.google.com/container-registry/docs/advanced-authentication)
  your local `docker` cli with your GCP container registry.
  {% endtab %}

{% tab title="Azure" %}

* [Set up](https://azure.microsoft.com/en-in/services/container-registry/#get-started)
  an Azure Container Registry (ACR) and create a repository (either public or
  private) with the name `zenml-kubeflow` . This is the repository to which
  ZenML will push your pipeline images to.
* Authenticate your local `docker` cli with your ACR registry using the
  following command.

  ```powershell
  az acr login --name REGISTRY_NAME
  ```

{% endtab %}
{% endtabs %}

### Artifact Store

{% tabs %}
{% tab title="AWS" %}

* [Create](https://docs.aws.amazon.com/AmazonS3/latest/userguide/create-bucket-overview.html)
  an Amazon S3 bucket in a region of your choice.
* Make sure that your EKS cluster is authorized to access the S3 bucket. This
  can be done in one of the following ways:
    * The simpler way is to add
      an [`AmazonS3FullAccess`](https://console.aws.amazon.com/iam/home#/policies/arn:aws:iam::aws:policy/AmazonS3FullAccess)
      policy to your cluster node group's IAM role.
    * The more complex way would be to create `ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
      and `AWS_SESSION_TOKEN` environment variables in your EKS cluster. This
      can be done by extending the `zenmldocker/zenml` image
      and [adding](https://docs.docker.com/engine/reference/builder/#env) these
      variables in a Dockerfile.
* The path for your bucket should be in this format `s3://your-bucket`.
  {% endtab %}

{% tab title="GCP" %}

* [Create](https://cloud.google.com/storage/docs/creating-buckets) a GCP Cloud
  Storage Bucket in a region of your choice.
* Make sure that your GKE cluster is authorized to access the GCS bucket.
* The path for your bucket should be in this format `gs://your-bucket`.
  {% endtab %}

{% tab title="Azure" %}

* [Create](https://docs.microsoft.com/en-us/azure/storage/common/storage-account-overview)
  an Azure Storage Account
  and [add](https://docs.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-portal)
  a _container_ to hold your _blobs._
* Open your storage account page on the Azure portal and follow these steps:
    * Keep the name of the storage account handy - it will be required in a
      later step.
    * From the navigation panel on the left, select **Access Keys** under **
      Security + networking**. Note any of the keys available there for future
      use.
* Make sure to set a combination of the following environment
  variables:`AZURE_STORAGE_CONNECTION_STRING` or `AZURE_STORAGE_ACCOUNT_NAME`
  and one of \[`AZURE_STORAGE_ACCOUNT_KEY`, `AZURE_STORAGE_SAS_TOKEN`]. \
  This can be done
    * On Linux/MacOS by exporting them in a
      terminal: `export AZURE_STORAGE_CONNECTION_STRING=<MY_CONNECTION_STRING>`.
    * On Windows by running the
      command `setx AZURE_STORAGE_CONNECTION_STRING "<MY_CONNECTION_STRING>"` in
      the Command Prompt.
    * In a docker image
      by [adding](https://docs.docker.com/engine/reference/builder/#env) these
      variables in a Dockerfile.
* The path for your bucket should be in this format: `az://<CONTAINER-NAME>`
  or `abfs://<CONTAINER_NAME>`. See [adlfs](https://github.com/fsspec/adlfs) (
  the package ZenML uses to access your Azure storage) for more details.
  {% endtab %}
  {% endtabs %}

### Metadata Store

{% hint style="info" %}

The **metadata store** requires a SQL compatible database service to store
information about pipelines, pipeline runs, steps and artifacts. If you want to
avoid using a managed cloud SQL database service, ZenML has the option to reuse
the gRPC metadata service installed and used internally by the Kubeflow
Pipelines deployment. This is not recommended for production use.

To use the Kubeflow Pipelines metadata service, use a metadata store of flavor
`kubeflow` in your stack configuration and ignore this section. 

{% endhint %}

{% hint style="info" %}

If you decide to use an SQL **metadata store** backed by a managed cloud SQL
database service, you will also need a matching **secrets manager** to store the
SSL credentials (i.e. certificates) required to connect to it.

{% endhint %}

{% tabs %}
{% tab title="AWS" %}

* [Set up](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_GettingStarted.html)
  an Amazon RDS database instance with a username and a password.
* Find the endpoint (DNS name) and TCP port number for your DB instance.
  You will need them to register with ZenML. The endpoint should be in the format
  `INSTANCE-NAME.ID.REGION.rds.amazonaws.com`.
* You may also have to explicitly reconfigure the VPC security group rules to allow
  access to the database from outside the cloud as well as from the EKS cluster
  (if they do not share the same VPC).
* It is strongly recommended to also [enable SSL access to your RDS database instance](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.SSL.html).
  This is done differently depending on the type of RDS service you use. For
  example, [for a MySQL RDS service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_MySQL.html#MySQL.Concepts.SSLSupport),
  you have to connect to the database using the `mysql` client and require SSL
  for the access for the user you created at the first step. You will also need
  the AWS server certificate associated with the AWS region where the RDS instance
  is running, as covered in the AWS documentation. Download the certificate as a
  file and have it ready for use during the ZenML stack registration.

{% endtab %}

{% tab title="GCP" %}

* Set up a [Google Cloud SQL database instance](https://cloud.google.com/sql).
  You should enable a public IP address for the database instance, if you want to
  access it from outside the GCP cloud e.g. to have access to the pipeline metadata
  from your local host. In the authorized networks section of the database instance,
  you should add a CIDR that covers all IP addresses that will access the database
  (e.g. the GKE cluster, your local host). If you don't know what these are, you
  should use a CIDR value of 0.0.0.0/0 that allows all IP addresses, but make sure
  to enable SSL access to the database.
* Find the public IP address and TCP port number for your DB instance.
  You will need them to register with ZenML.
* It is strongly recommended to enable SSL encryption for your database instance
  and allow only SSL connections. Also create a client certificate and key pair
  that you will use to connect ZenML to the database. You should have three
  files saved to your machine: a server certificate, a client certificate and a
  client key. You will need all three during the ZenML stack registration.
  {% endtab %}

{% tab title="Azure" %}

The Azure SQL metadata service is not yet supported because ZenML doesn't yet
support a matching Azure secrets manager.

{% endtab %}
{% endtabs %}

## Integrating with ZenML

To run our pipeline on Kubeflow Pipelines deployed to cloud, we will create a
new stack with these components that you have just created.

1. Install the cloud provider and the `kubeflow` plugin

    ```powershell
    zenml integration install <aws s3/gcp/azure>
    zenml integration install kubeflow
    ```

2. Register the metadata store component

   * if you decided to use the Kubeflow metadata service, you can configure a
     `kubeflow` flavor metadata-store:

    ```powershell
    zenml metadata-store register cloud_metadata_store --flavor=kubeflow
    ```
   * otherwise, configure a `mysql` flavor metadata-store. You will also need a
     secrets manager component to store the MySQL credentials and a secret (named
     `mysql_secret` in the example) to be registered after the stack (step 5.).

    ```powershell
    zenml metadata-store register cloud_metadata_store --flavor=mysql --secret=mysql_secret
    ```

3. Register the other stack components and the stack itself

    ```powershell
    zenml container-registry register cloud_registry --flavor=<aws/gcp/azure> --uri=$PATH_TO_YOUR_CONTAINER_REGISTRY
    zenml orchestrator register cloud_orchestrator --flavor=kubeflow --custom_docker_base_image_name=YOUR_IMAGE
    zenml artifact-store register cloud_artifact_store --flavor=<s3/gcp/azure> --path=$PATH_TO_YOUR_BUCKET
    zenml secrets-manager register cloud_secrets_manager --flavor=<aws/gcp/azure> 

    # Register the cloud stack
    zenml stack register cloud_kubeflow_stack -m cloud_metadata_store -a cloud_artifact_store -o cloud_orchestrator -c cloud_registry -x cloud_secrets_manager
    ```

4. Activate the newly created stack.

    ```powershell
    zenml stack set cloud_kubeflow_stack
    ```


5. Create the secret for the `mysql` metadata store (not necessary if you used
a `kubeflow` flavor metadata-store).

    ```powershell
    zenml secret register mysql_secret --schema=mysql --user=<user> --password=<password>
    --ssl_ca=@/path/to/downloaded/server-cert --ssl_cert=@/path/to/downloaded/client-cert
    --ssl_key=@/path/to/downloaded/client-key
    ```

6. Do a pipeline run and check your Kubeflow UI to see it running there! 🚀

{% hint style="info" %}

* The **secrets manager** is only required if you're using a **metadata store**
  backed by a managed cloud database service.
* The **metadata store** secret user, password and SSL certificates are the ones
  set up and downloaded during the creation of the managed SQL database service.
* The `--ssl_cert` and `--ssl_key` parameters for the `mysql_secret` are only
  required if you set up client certificates for the MySQL service.
* You can choose any name for your stack components apart from the ones used in
  the script above.
  {% endhint %}

{% hint style="warning" %}
Make sure to replace `$PATH_TO_YOUR_BUCKET`
and `$PATH_TO_YOUR_CONTAINER_REGISTRY` with the actual URIs of your bucket and
container registry.
{% endhint %}
