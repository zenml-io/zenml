---
description: Orchestrate using cloud resources.
---

# Orchestrating pipelines on the cloud

Until now, we've only run pipelines locally. The next step is get free from our local machines, and transition our pipelines to execute on the cloud. This will enable you to run your MLOps pipelines in a cloud environment, leveraging the scalability and robustness that cloud platforms offer.

In order to do this, we need to get familiar with two more stack components: 

- The [orchestrator](../../stacks-and-components/component-guide/orchestrators/) manages the workflow and execution of your pipelines.
- The [container registry](../../stacks-and-components/component-guide/container-registries/) is a storage and content delivery system that holds your Docker container images.

These, along with with [remote storage](remote-storage.md) completes a basic cloud stack where our pipeline is entirely running on the cloud. 

## Starting with a basic cloud stack

The easiest cloud orchestrator to start with is the [Skypilot](https://skypilot.readthedocs.io/) orchestrator running on a public cloud. The advantage of Skypilot is that it simply provisions a VM on your cloud provider, which is the simplest way to get started on the cloud.  

Coupled with Skypilot, we need a mechanism to package your code and ship it to the cloud for Skypilot to do its thing. ZenML uses [Docker](https://www.docker.com/) to achieve this. Every time you run a pipeline with a remote orchestrator, ZenML builds an image for the entire pipeline (and optionally each step of a pipeline depending on your [configuration](../advanced-guide/infrastructure-management/containerize-your-pipeline.md)). This image contains the code, requirements, and everything else needed to run the steps of the pipeline in any environment. ZenML then pushes this image to the container registry configured in your stack, and the orchestrator pulls the image when its ready to execute a step.

To summarize, here is the broad sequence of events that happen when you run a pipeline with such a cloud stack:

<figure><img src="../../.gitbook/assets/cloud_orchestration_run.png" alt=""><figcaption><p>Sequence of events that happen when running a pipeline on a full cloud stack.</p></figcaption></figure>

1. The user runs a pipeline on the client machine.
2. The client asks the server for the stack info, which returns it with the configuration of the cloud stack.
3. Based on the stack info and pipeline specification, client builds and pushes image to the `container registry`. The image contains the environment needed to execute the pipeline and the code of the steps.
4. The client creates a run in the `orchestrator`. For example, in the case of the [Skypilot](https://skypilot.readthedocs.io/) orchestrator, it creates a virtual machine in the cloud with some commands to pull and run a docker image from the specified container registry.  
5. The `orchestrator` pulls the appropriate image from the `container registry` as its executing the pipeline (each step has an image).
6. As each pipeline runs, it stores artifacts physically in the `artifact store`. Of course, this artifact store needs to be some form of cloud storage.
7. As each pipeline runs, it reports status back to the zenml server, and optionally queries the server for metadata.

## Provisioning and registering a Skypilot orchestrator alongside a container registry

While there are detaled docs on [how to setup a Skypilot orchestrator](../../stacks-and-components/component-guide/orchestrators/skypilot-vm.md) and a [container registry](../../stacks-and-components/component-guide/container-registries/container-registries.md) on each public cloud, we have put the most relevant details here for convenience:

{% tabs %}
{% tab title="AWS" %}
You will need to install and set up the AWS CLI on your machine as a
prerequisite, as covered in [the AWS CLI documentation](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html), before
you register the S3 Artifact Store.

The Amazon Web Services S3 Artifact Store flavor is provided by the [S3 ZenML integration](../../stacks-and-components/component-guide/artifact-stores/s3.md), you need to install it on your local machine to be able to register an S3 Artifact Store and add it to your stack:

```shell
zenml integration install s3 -y
```

{% hint style="info" %}
Having trouble with this command? You can use `poetry` or `pip` to install the requirements of any ZenML integration directly. In order to obtain the exact requirements of the GCP integrations you can use `zenml integration requirements s3`.
{% endhint %}

The only configuration parameter mandatory for registering an S3 Artifact Store is the root path URI, which needs to point to an S3 bucket and take the form `s3://bucket-name`. In order to create a S3 bucket, refer to the [AWS documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/create-bucket-overview.html).

With the URI to your S3 bucket known, registering an S3 Artifact Store can be done as follows:

```shell
# Register the S3 artifact-store
zenml artifact-store register remote_artifact_store -f s3 --path=s3://bucket-name
```

For more information, read the [dedicated S3 artifact store flavor guide](../../stacks-and-components/component-guide/artifact-stores/s3.md).
{% endtab %}
{% tab title="GCP" %}
You will need to install and set up the Google Cloud CLI on your machine as a prerequisite, as covered in [the Google Cloud documentation](https://cloud.google.com/sdk/docs/install-sdk) , before you register the GCS Artifact Store.

The Google Cloud Storage Artifact Store flavor is provided by the [GCP ZenML integration](../../stacks-and-components/component-guide/artifact-stores/gcp.md), you need to install it on your local machine to be able to register a GCS Artifact Store and add it to your stack:

```shell
zenml integration install gcp -y
```

{% hint style="info" %}
Having trouble with this command? You can use `poetry` or `pip` to install the requirements of any ZenML integration directly. In order to obtain the exact requirements of the GCP integrations you can use `zenml integration requirements gcp`.
{% endhint %}

The only configuration parameter mandatory for registering a GCS Artifact Store is the root path URI, which needs to point to a GCS bucket and take the form `gs://bucket-name`. Please
read [the Google Cloud Storage documentation](https://cloud.google.com/storage/docs/creating-buckets) on how to provision a GCS bucket.

With the URI to your GCS bucket known, registering a GCS Artifact Store can be done as follows:

```shell
# Register the GCS artifact store
zenml artifact-store register remote_artifact_store -f gcp --path=gs://bucket-name
```

For more information, read the [dedicated GCS artifact store flavor guide](../../stacks-and-components/component-guide/artifact-stores/gcp.md).
{% endtab %}
{% tab title="Azure" %}
You will need to install and set up the Azure CLI on your machine as a prerequisite, as covered in [the Azure documentation](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli), before you register the Azure Artifact Store.

The Microsoft Azure Artifact Store flavor is provided by the [Azure ZenML integration](../../stacks-and-components/component-guide/artifact-stores/azure.md), you need to install it on your local machine to be able to register an Azure Artifact Store and add it to your stack:

```shell
zenml integration install azure -y
```

{% hint style="info" %}
Having trouble with this command? You can use `poetry` or `pip` to install the requirements of any ZenML integration directly. In order to obtain the exact requirements of the GCP integrations you can use `zenml integration requirements azure`.
{% endhint %}

The only configuration parameter mandatory for registering an Azure Artifact Store is the root path URI, which needs to
point to an Azure Blog Storage container and take the form `az://container-name` or `abfs://container-name`. Please
read [the Azure Blob Storage documentation](https://docs.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-portal)
on how to provision an Azure Blob Storage container.

With the URI to your Azure Blob Storage container known, registering an Azure Artifact Store can be done as follows:

```shell
# Register the Azure artifact store
zenml artifact-store register remote_artifact_store -f azure --path=az://container-name
```

For more information, read the [dedicated Azure artifact store flavor guide](../../stacks-and-components/component-guide/artifact-stores/azure.md).
{% endtab %}
{% tab title="Other" %}
You can create a remote stack on pretty much any environment, including other cloud providers such as Lambda Cloud, Paperspace etc. A cloud agnostic stack would use the [Kubernetes](../../stacks-and-components/component-guide/orchestrators/kubernetes.md) orchestrator, a [Minio artifact store](../../stacks-and-components/component-guide/artifact-stores/artifact-stores.md), and a [default container registry](../../stacks-and-components/component-guide/container-registries/default.md).

It is also relatively simple to create a [custom orchestrator flavor](../../stacks-and-components/custom-solutions/implement-a-custom-stack-component.md) for your use case.
{% endtab %}
{% endtabs %}

{% hint style="info" %}
Having trouble with setting up infrastructure? Try reading the [stack deployment](../../stacks-and-components/stack-deployment/) section of the docs to gain more insight. If it still doesn't work, join the [ZenML community](https://zenml.io/slack) and ask!
{% endhint %}

Please note that your local client needs to be authenticated to the cloud CLI, and have sufficient permissions to push a container to your container registry , and deploy a VM using Skypilot. However, it is no longer neccessary to have direct access to the remote artifact storage, as the pipeline executes in a VM on the cloud. Of course, that means the provisioned VM now needs access to the remote storage instead!

It is important to understand at the infrastructure level how services authenticate with each other. This can get quite complex, and ZenML has a concept called [Service Connectors](../../stacks-and-components/auth-management/auth-management.md) that simplifies this. If you're curious, read that section of the docs!

## Running a pipeline on a cloud stack

Now that we have our remote artifact store registered, we can [register a new stack](understand-stacks.md#registering-a-stack) with it, just like we did in the previous chapter:

{% tabs %}
{% tab title="CLI" %}
```shell
zenml stack register local_with_remote_storage -o default -a my_artifact_store
```
{% endtab %}
{% tab title="Dashboard" %}
<figure><img src="../../.gitbook/assets/CreateStack.png" alt=""><figcaption><p>Register a new stack.</p></figcaption></figure>
{% endtab %}
{% endtabs %}

Now, using the [code from the previous chapter](understand-stacks.md#run-a-pipeline-on-the-new-local-stack), we run a training
pipeline:

Set the cloud stack active:

```shell
zenml stack set local_with_remote_storage
```

Run the training pipeline:
```shell
python run.py --training-pipeline
```

For more detailed information on each step and additional cloud provider configurations, please refer to the [Stack deployment](../../stacks-and-components/stack-deployment/stack-deployment.md) and [Component Guide](../../stacks-and-components/component-guide/) sections of the ZenML documentation.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
