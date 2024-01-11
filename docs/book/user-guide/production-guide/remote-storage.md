---
description: Transitioning to remote artifact storage.
---

# Chapter 3: Connecting Remote Storage

In the previous chapters, we've been working with artifacts stored locally on our machines. This setup is fine for individual experiments, but as we move towards a collaborative and production-ready environment, we need a solution that is more robust, shareable, and scalable. Enter remote storage.

Remote storage allows us to store our artifacts in the cloud, which means they're accessible from anywhere and by anyone with the right permissions. This is essential for team collaboration and for managing the larger datasets and models that come with production workloads.

When using a stack with remote storage, nothing changes except the fact that the artifacts
get materialized in a central, remote, storage location. This diagram explains the flow:

<figure><img src="../../.gitbook/assets/local_run_with_remote_artifact_store.png" alt=""><figcaption><p>Sequence of events that happen when running a pipeline on a remote artifact store.</p></figcaption></figure>

## Provisioning and registering a remote artifact store

Out of the box, ZenML ships with [many different supported artifact store flavors](../../stacks-and-components/component-guide/artifact-stores/). For convenience, here are some brief instructions on how to quickly get up and running on the major cloud providers:

{% tabs %}
{% tab title="AWS" %}
The Amazon Web Services S3 Artifact Store flavor is provided by the [S3 ZenML integration](../../stacks-and-components/component-guide/artifact-stores/s3.md), you need to install it on your local machine to be able to register an S3 Artifact Store and add it to your stack:

```shell
zenml integration install s3 -y
```

{% hint style="info" %}
Having trouble with this this command? You can use `poetry` or `pip` to install the requirements of any ZenML integration directly. In order to obtain the exact requirements of the GCP integrations you can use `zenml integration requirements s3`.
{% endhint %}

The only configuration parameter mandatory for registering an S3 Artifact Store is the root path URI, which needs to point to an S3 bucket and take the form `s3://bucket-name`. In order to create a S3 bucket, refer to the [AWS documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/create-bucket-overview.html).

With the URI to your S3 bucket known, registering an S3 Artifact Store can be done as follows:

```shell
# Register the S3 artifact-store
zenml artifact-store register remote_artifact_store -f s3 --path=s3://bucket-name
```
{% endtab %}
{% tab title="GCP" %}
The Google Cloud Storage Artifact Store flavor is provided by the [GCP ZenML integration](../../stacks-and-components/component-guide/artifact-stores/gcp.md), you need to install it on your local machine to be able to register a GCS Artifact Store and add it to your stack:

```shell
zenml integration install gcp -y
```

{% hint style="info" %}
Having trouble with this this command? You can use `poetry` or `pip` to install the requirements of any ZenML integration directly. In order to obtain the exact requirements of the GCP integrations you can use `zenml integration requirements gcp`.
{% endhint %}

The only configuration parameter mandatory for registering a GCS Artifact Store is the root path URI, which needs to point to a GCS bucket and take the form `gs://bucket-name`. Please
read [the Google Cloud Storage documentation](https://cloud.google.com/storage/docs/creating-buckets) on how to provision a GCS bucket.

With the URI to your GCS bucket known, registering a GCS Artifact Store can be done as follows:

```shell
# Register the GCS artifact store
zenml artifact-store register remote_artifact_store -f gcp --path=gs://bucket-name
```
{% endtab %}
{% tab title="Azure" %}
The Microsoft Azure Artifact Store flavor is provided by the [Azure ZenML integration](../../stacks-and-components/component-guide/artifact-stores/azure.md), you need to install it on your local machine to be able to register an Azure Artifact Store and add it to your stack:

```shell
zenml integration install azure -y
```

{% hint style="info" %}
Having trouble with this this command? You can use `poetry` or `pip` to install the requirements of any ZenML integration directly. In order to obtain the exact requirements of the GCP integrations you can use `zenml integration requirements azure`.
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
{% endtab %}
{% tab title="Other" %}
You can create a remote artifact store on pretty much any environment, including other cloud providers using a cloud-agnostic artifact storage such as [Minio](../../stacks-and-components/component-guide/artifact-stores/artifact-stores.md).

It is also relatively simple to create a [custom stack component flavor](../../stacks-and-components/custom-solutions/implement-a-custom-stack-component.md) for your use-case.
{% endtab %}
{% endtabs %}

{% hint style="info" %}
Having trouble with deployment? Try reading the [stack deployment](../../stacks-and-components/stack-deployment/) section of the docs to troubleshoot. If it still doesn't work, join the [ZenML community](https://zenml.io/slack) and post your traceback!
{% endhint %}

Feel free to play around with some of the configuration provided in the above commands depending your needs. Please notice that we are also creating [service connectors](../../stacks-and-components/auth-management/auth-management.md) and associating them with the stack components with the above command. While service connectors are advanced concepts, for now it is sufficient to understand that these connectors give the deployed ZenML server the same credentials as your local ones.

If you would like to not give any credentials to the ZenML server for your cloud provider, you can simply ignore service connector specific commands above.

## Running a pipeline on a cloud stack

With the new stack deployed and configured in ZenML, running a pipeline will now behave differently. Let's use the starter project from the [previous guide](../starter-guide/starter-project.md) to see it in action.

If you have not already, clone the starter template:

```bash
pip install "zenml[templates,server]" notebook
zenml integration install sklearn -y
mkdir zenml_starter
cd zenml_starter
zenml init --template starter --template-with-defaults

# Just in case, we install the requirements again
pip install -r requirements.txt
```

<details>

<summary>Above doesn't work? Here is an alternative</summary>

The starter template is the same as the [ZenML quickstart](https://github.com/zenml-io/zenml/tree/main/examples/quickstart). You can clone it like so:

```bash
git clone git@github.com:zenml-io/zenml.git
cd examples/quickstart
pip install -r requirements.txt
zenml init
```

</details>

Set the cloud stack active:

```shell
zenml stack set NAME_OF_STACK
```

Run the training pipeline:
```shell
python run.py --training-pipeline
```

1. The user runs a pipeline on the client machine (in this case the training pipeline of the starter template).
2. The client asks the server for the stack info, which returns it with the configuration of the cloud stack.
3. Based on the stack info and pipeline specification, client builds and pushes image to the `container registry`. The image contains the environment needed to execute the pipeline and the code of the steps.
4. The client creates a run in the `orchestrator`. In this case, we are leveraging the [Skypilot](https://skypilot.readthedocs.io/) orchestrator to create a virtual machine in the cloud and run our code on it.  
5. The `orchestrator` pulls the appropriate image from the `container registry` as its executing the pipeline (each step has an image).
6. As each pipeline runs, it stores artifacts physically in the `artifact store`.
7. As each pipeline runs, it reports status back to the zenml server, and optionally queries the server for metadata.

For more detailed information on each step and additional cloud provider configurations, please refer to the [Stack deployment](../../stacks-and-components/stack-deployment/stack-deployment.md) and [Component Guide](../../stacks-and-components/component-guide/) sections of the ZenML documentation.

With your remote Artifact Store configured and connected, you can set it as part of a new stack or update an existing stack. When you run your pipelines, ZenML will automatically store the artifacts in the specified remote storage, ensuring that they are preserved and accessible for future runs and by your team members.


By connecting remote storage, you're taking a significant step towards building a collaborative and scalable MLOps workflow. Your artifacts are no longer tied to a single machine but are now part of a cloud-based ecosystem, ready to be shared and built upon.

In the next chapter, we'll dive deeper into orchestrating our pipelines in the cloud, leveraging the full potential of our newly established remote storage capabilities.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>