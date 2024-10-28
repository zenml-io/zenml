---
description: Deploy a cloud stack using Terraform
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Deploy a cloud stack with Terraform

ZenML maintains a collection of [Terraform modules](https://registry.terraform.io/modules/zenml-io/zenml-stack)
designed to streamline the provisioning of cloud resources and seamlessly
integrate them with ZenML Stacks. These modules simplify the setup process,
allowing users to quickly provision cloud resources as well as configure and
authorize ZenML to utilize them for running pipelines and other AI/ML operations.

By leveraging these Terraform modules, users can ensure a more efficient and
scalable deployment of their machine learning infrastructure, ultimately
enhancing their development and operational workflows. The modules'
implementation can also be used as a reference for creating custom Terraform
configurations tailored to specific cloud environments and requirements.

{% hint style="info" %}
Terraform requires you to manage your infrastructure as code yourself. Among
other things, this means that you will need to have Terraform installed on your
machine and you will need to manually manage the state of your infrastructure.

If you prefer a more automated approach, you can use [the 1-click stack deployment feature](deploy-a-cloud-stack.md)
to deploy a cloud stack with ZenML with minimal knowledge of Terraform or cloud
infrastructure for that matter.

If you have the required infrastructure pieces already deployed on your cloud, 
you can also use [the stack wizard to seamlessly register your stack](../../how-to/stack-deployment/register-a-cloud-stack.md).
{% endhint %}

## Pre-requisites

To use this feature, you need a deployed ZenML server instance that is reachable
from the cloud provider where you wish to have the stack provisioned (this can't
be a local server started via `zenml up`). If you do not already have one set up,
you [can register for a free ZenML Pro account](https://cloud.zenml.io/signup)
or you can learn about self-hosting a ZenML server [here](../../getting-started/deploying-zenml/README.md).

Once you are connected to your deployed ZenML server, you need to create
a service account and an API key for it. You will use the API key to give the
Terraform module programmatic access to your ZenML server. You can find more
about service accounts and API keys [here](../connecting-to-zenml/connect-with-a-service-account.md).
but the process is as simple as running the following CLI command while
connected to your ZenML server:

```shell
zenml service-account create <account-name>
```

Example output:

```shell
$ zenml service-account create terraform-account
Created service account 'terraform-account'.
Successfully created API key `default`.
The API key value is: 'ZENKEY_...'
Please store it safely as it will not be shown again.
To configure a ZenML client to use this API key, run:

zenml connect --url https://842ed6a9-zenml.staging.cloudinfra.zenml.io --api-key \
    'ZENKEY_...'
```

Finally, you will need the following on the machine where you will be running
Terraform:

* [Terraform](https://www.terraform.io/downloads.html) installed on your machine
(version at least 1.9).
* the ZenML Terraform stack modules assume you are already locally authenticated
with your cloud provider through the provider's CLI or SDK tool and have
permissions to create the resources that the modules will provision. This is
different depending on the cloud provider you are using and is covered in the
following sections.

## How to use the Terraform stack deployment modules

If you are already knowledgeable with using Terraform and the cloud provider
where you want to deploy the stack, this process will be straightforward. In a
nutshell, you will need to:

1. create a new Terraform configuration file (e.g., `main.tf`), preferably in a
new directory, with the content that looks like this (`<cloud provider>` can be
`aws`, `gcp`, or `azure`):

```hcl
module "zenml_stack" {
  source = "zenml-io/zenml-stack/<cloud-provider>"
  version = "x.y.z"

  # Required inputs
  zenml_server_url = "https://<zenml-server-url>"
  zenml_api_key = "<your-api-key>"
  # Optional inputs
  zenml_stack_name = "<your-stack-name>"
  orchestrator = "<your-orchestrator-type>" # e.g., "local", "sagemaker", "vertex", "azureml", "skypilot"
}
output "zenml_stack_id" {
  value = module.zenml_stack.zenml_stack_id
}
output "zenml_stack_name" {
  value = module.zenml_stack.zenml_stack_name
}
```

There might be a few additional required or optional inputs depending on the
cloud provider you are using. You can find the full list of inputs for each
module in the [Terraform Registry](https://registry.terraform.io/modules/zenml-io/zenml-stack)
documentation for the relevant module or you can read on in the following
sections.

2. Run the following commands in the directory where you have your Terraform
configuration file:

```shell
terraform init
terraform apply
```

{% hint style="warning" %}
The directory where you keep the Terraform configuration file and where you run
the `terraform` commands is important. This is where Terraform will store the
state of your infrastructure. Make sure you do not delete this directory or the
state file it contains unless you are sure you no longer need to manage these
resources with Terraform or after you have deprovisioned them up with
`terraform destroy`.
{% endhint %}

3. Terraform will prompt you to confirm the changes it will make to your cloud
infrastructure. If you are happy with the changes, type `yes` and hit enter.

4. Terraform will then provision the resources you have specified in your
configuration file. Once the process is complete, you will see a message
indicating that the resources have been successfully created and printing out
the ZenML stack ID and name:

```shell
...
Apply complete! Resources: 15 added, 0 changed, 0 destroyed.

Outputs:

zenml_stack_id = "04c65b96-b435-4a39-8484-8cc18f89b991"
zenml_stack_name = "terraform-gcp-588339e64d06"
```

At this point, a ZenML stack has also been created and registered with your
ZenML server and you can start using it to run your pipelines:

```shell
zenml integration install <list-of-required-integrations>
zenml stack set <zenml_stack_id>
```

You can find more details specific to the cloud provider of your choice in the
next section:

{% tabs %}
{% tab title="AWS" %}

The [original documentation for the ZenML AWS Terraform module](https://registry.terraform.io/modules/zenml-io/zenml-stack/aws/latest)
contains extensive information about required permissions, inputs, outputs and
provisioned resources. This is a summary of the key points from that
documentation.

### Authentication

To authenticate with AWS, you need to have [the AWS CLI](https://aws.amazon.com/cli/)
installed on your machine and you need to have run `aws configure` to set up your
credentials.

### Example Terraform Configuration

Here is an example Terraform configuration file for deploying a ZenML stack on
AWS:

```hcl
module "zenml_stack" {
  source = "zenml-io/zenml-stack/aws"

  # Required inputs
  zenml_server_url = "https://<zenml-server-url>"
  zenml_api_key = "<your-api-key>"

  # Optional inputs
  region = "<your-aws-region>"
  orchestrator = "<your-orchestrator-type>" # e.g., "local", "sagemaker", "skypilot"
}
output "zenml_stack_id" {
  value = module.zenml_stack.zenml_stack_id
}
output "zenml_stack_name" {
  value = module.zenml_stack.zenml_stack_name
}
```

### Stack Components

The Terraform module will create a ZenML stack configuration with the
following components:


1. an S3 Artifact Store linked to a S3 bucket
2. an ECR Container Registry linked to a ECR repository
3. depending on the `orchestrator` input variable:
  * a local Orchestrator, if `orchestrator` is set to `local`. This can be used in combination with the SageMaker Step Operator to selectively run some steps locally and some on SageMaker.
  * a SageMaker Orchestrator linked to the AWS account, if `orchestrator` is set to `sagemaker` (default)
  * a SkyPilot Orchestrator linked to the AWS account, if `orchestrator` is set to `skypilot`
4. a SageMaker Step Operator linked to the AWS account
5. an AWS Service Connector configured with the IAM role credentials and used to
authenticate all ZenML components with your AWS account

To use the ZenML stack, you will need to install the required integrations:

* for the local or SageMaker orchestrator:

```shell
zenml integration install aws s3
```

* for the SkyPilot orchestrator:

```shell
zenml integration install aws s3 skypilot_aws
```

{% endtab %}
{% tab title="GCP" %}

The [original documentation for the ZenML GCP Terraform module](https://registry.terraform.io/modules/zenml-io/zenml-stack/gcp/latest)
contains extensive information about required permissions, inputs, outputs and
provisioned resources. This is a summary of the key points from that
documentation.

### Authentication

To authenticate with GCP, you need to have [the `gcloud` CLI](https://cloud.google.com/sdk/gcloud)
installed on your machine, and you need to have run `gcloud init` or `gcloud auth application-default login`
to set up your credentials.

### Example Terraform Configuration

Here is an example Terraform configuration file for deploying a ZenML stack on
AWS:

```hcl
module "zenml_stack" {
  source = "zenml-io/zenml-stack/gcp"

  # Required inputs
  project_id = "<your-gcp-project-id>"
  zenml_server_url = "https://<zenml-server-url>"
  zenml_api_key = "<your-api-key>"

  # Optional inputs
  region = "<your-gcp-region>"
  orchestrator = "<your-orchestrator-type>" # e.g., "local", "vertex", "skypilot" or "airflow"
}
output "zenml_stack_id" {
  value = module.zenml_stack.zenml_stack_id
}
output "zenml_stack_name" {
  value = module.zenml_stack.zenml_stack_name
}
```

### Stack Components

The Terraform module will create a ZenML stack configuration with the
following components:

1. an GCP Artifact Store linked to a GCS bucket
2. an GCP Container Registry linked to a Google Artifact Registry
3. depending on the `orchestrator` input variable:
  * a local Orchestrator, if `orchestrator` is set to `local`. This can be used in combination with the Vertex AI Step Operator to selectively run some steps locally and some on Vertex AI.
  * a Vertex AI Orchestrator linked to the GCP project, if `orchestrator` is set to `vertex` (default)
  * a SkyPilot Orchestrator linked to the GCP project, if `orchestrator` is set to `skypilot`
  * an Airflow Orchestrator linked to the Cloud Composer environment, if `orchestrator` is set to `airflow`
4. a Google Cloud Build Image Builder linked to your GCP project
5. a Vertex AI Step Operator linked to the GCP project
6. a GCP Service Connector configured with the GCP service account credentials or the GCP Workload Identity Provider configuration and used to authenticate all ZenML components with the GCP resources

To use the ZenML stack, you will need to install the required integrations:

* for the local and Vertex AI orchestrators:

```shell
zenml integration install gcp
```

* for the SkyPilot orchestrator:

```shell
zenml integration install gcp skypilot_gcp
```

* for the Airflow orchestrator:

```shell
zenml integration install gcp airflow
```

{% endtab %}
{% tab title="Azure" %}

The [original documentation for the ZenML Azure Terraform module](https://registry.terraform.io/modules/zenml-io/zenml-stack/azure/latest)
contains extensive information about required permissions, inputs, outputs and
provisioned resources. This is a summary of the key points from that
documentation.

### Authentication

To authenticate with Azure, you need to have [the Azure CLI](https://learn.microsoft.com/en-us/cli/azure/)
installed on your machine and you need to have run `az login` to set up your
credentials.

### Example Terraform Configuration

Here is an example Terraform configuration file for deploying a ZenML stack on
AWS:

```hcl
module "zenml_stack" {
  source = "zenml-io/zenml-stack/azure"

  # Required inputs
  zenml_server_url = "https://<zenml-server-url>"
  zenml_api_key = "<your-api-key>"

  # Optional inputs
  location = "<your-azure-location>"
  orchestrator = "<your-orchestrator-type>" # e.g., "local", "skypilot_azure"
}
output "zenml_stack_id" {
  value = module.zenml_stack.zenml_stack_id
}
output "zenml_stack_name" {
  value = module.zenml_stack.zenml_stack_name
}
```

### Stack Components

The Terraform module will create a ZenML stack configuration with the
following components:

1. an Azure Artifact Store linked to an Azure Storage Account and Blob Container
2. an ACR Container Registry linked to an Azure Container Registry
3. depending on the `orchestrator` input variable:
  * a local Orchestrator, if `orchestrator` is set to `local`. This can be used in combination with the AzureML Step Operator to selectively run some steps locally and some on AzureML.
  * an Azure SkyPilot Orchestrator linked to the Azure subscription, if `orchestrator` is set to `skypilot` (default)
  * an AzureML Orchestrator linked to an AzureML Workspace, if `orchestrator` is set to `azureml` 
4. an AzureML Step Operator linked to an AzureML Workspace
5. an Azure Service Connector configured with Azure Service Principal
credentials and used to authenticate all ZenML components with the Azure resources

To use the ZenML stack, you will need to install the required integrations:

* for the local and AzureML orchestrators:

```shell
zenml integration install azure
```

* for the SkyPilot orchestrator:

```shell
zenml integration install azure skypilot_azure
```

{% endtab %}
{% endtabs %}

## How to clean up the Terraform stack deployments

Cleaning up the resources provisioned by Terraform is as simple as running the
`terraform destroy` command in the directory where you have your Terraform
configuration file. This will remove all the resources that were provisioned by
the Terraform module and will also delete the ZenML stack that was registered
with your ZenML server.

```shell
terraform destroy
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
