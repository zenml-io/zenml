---
description: Provision infrastructure on the cloud.
---

# Deploying a Cloud Stack

The next step is to scale our pipelines to the cloud. In order to do this, we need to configure a basic cloud stack in ZenML. This typically consists of three key components that we have learned about in the last section:

- The [orchestrator](../../stacks-and-components/component-guide/orchestrators/) manages the workflow and execution of your pipelines.
- The [artifact store](../../stacks-and-components/component-guide/artifact-stores/) is where your pipeline artifacts, such as datasets and models, are stored.
- The [container registry](../../stacks-and-components/component-guide/container-registries/) is a storage and content delivery system that holds your Docker container images.

In this chapter, we'll walk you through the process of deploying a basic cloud stack on a public cloud provider. This will enable you to run your MLOps pipelines in a cloud environment, leveraging the scalability and robustness that cloud platforms offer.

## Deploying on a public cloud

To get a minimal cloud stack running quickly, ZenML integrates with the [MLStacks](https://mlstacks.zenml.io/getting-started/introduction) project. Before we begin, ensure you have:

- An account with your chosen cloud provider.
- The cloud provider's CLI installed and configured with the necessary permissions.
- The `zenml` CLI installed and configured on your local machine with the [MLStacks](https://mlstacks.zenml.io/getting-started/introduction) extra (i.e. `pip install "zenml[mlstacks]"`).
- MLStacks uses Terraform on the backend to manage infrastructure. You will need to have Terraform installed. Please visit [the Terraform docs](https://learn.hashicorp.com/tutorials/terraform/install-cli#install-terraform) for installation instructions.
- MLStacks also uses Helm to deploy Kubernetes resources. You will need to have Helm installed. Please visit [the Helm docs](https://helm.sh/docs/intro/install/#from-script) for installation instructions.
{% endhint %}

Then we can start deploying infrastructure (Note that from this point on, charges will be incurred on your cloud provider):

{% tabs %}
{% tab title="GCP" %}
Deploying a basic stack on GCP involves setting up a [Skypilot](https://skypilot.readthedocs.io/) orchestrator, a Google Cloud Storage (GCS) artifact store, and a Google Container Registry (GCR). Follow these steps to deploy your stack:

1. Deploy the stack using ZenML's CLI:

    ```bash
    zenml stack deploy -n basic -p gcp -a -c -r us-east1 -x bucket_name=<SOME_NEW_BUCKET_NAME> -x project_id=<YOUR_GCP_PROJECT_ID> -o skypilot
    ```

    Replace `<SOME_NEW_BUCKET_NAME>` with a unique name for your GCP storage bucket and `<YOUR_GCP_PROJECT_ID>` with your GCP project ID.

2. Register a service connector for GCP:

    ```bash
    zenml service-connector register gcp-generic --type gcp --auto-configure
    ```

3. Connect the artifact store to GCS:

    ```bash
    zenml artifact-store connect gcs_artifact_store --connector gcp-generic
    ```

4. Connect the orchestrator to Skypilot:

    ```bash
    zenml orchestrator connect gcp_skypilot_orchestrator --connector gcp-generic
    ```

5. Connect the container registry to GCR:

    ```bash
    zenml container-registry connect gcr_container_registry --connector gcp-generic
    ```

By completing these steps, you'll have a fully functional ZenML stack on GCP, ready for your production MLOps pipelines.
{% endtab %}
{% tab title="AWS" %}
Deploying a basic stack on AWS involves setting up a [Skypilot](https://skypilot.readthedocs.io/), an Amazon Simple Storage Service (S3) artifact store, and an Amazon Elastic Container Registry (ECR). Follow these steps to deploy your stack:

1. Deploy the stack using ZenML's CLI:

    ```bash
    zenml stack deploy -n basic -p aws -a -c -r us-east-1 -x bucket_name=<SOME_NEW_BUCKET_NAME> -o skypilot
    ```

    Replace `<SOME_NEW_BUCKET_NAME>` with a unique name for your AWS S3 bucket.

2. Register a service connector for AWS:

    ```bash
    zenml service-connector register aws-generic --type aws --auto-configure
    ```

3. Connect the artifact store to S3:

    ```bash
    zenml artifact-store connect s3_artifact_store --connector aws-generic
    ```

4. Connect the orchestrator to Skypilot:

    ```bash
    zenml orchestrator connect aws_skypilot_orchestrator --connector aws-generic
    ```

5. Connect the container registry to AWS ECR:

    ```bash
    zenml container-registry connect aws_container_registry --connector aws-generic
    ```

By following these steps, you'll have a ZenML stack on AWS that's ready to handle your MLOps needs in the cloud.
{% endtab %}
{% endtabs %}

{% hint style="info" %}
Having trouble with deployment? Try reading the [stack deployment](../../stacks-and-components/stack-deployment/) section of the docs to troubleshoot. If it still doesn't work, join the [ZenML community](https://zenml.io/slack) and post your traceback!
{% endhint %}

Feel free to play around with some of the configuration provided in the above commands depending your needs. Please notice that we are also creating [service connectors](../../stacks-and-components/auth-management/auth-management.md) and associating them with the stack components with the above command. While service connectors are advanced concepts, for now it is sufficient to understand that these connectors give the deployed ZenML server the same credentials as your local ones.

If you would like to not give any credentials to the ZenML server for your cloud provider, you can simply ignore service connector specific commands above.

## Running a pipeline on a cloud stack

With the new stack deployed and configured in ZenML, running a pipeline will now behave differently. Let's use the starter project from the [previous guide](../starter-guide/starter-project.md) to see it in action.

### Get our code ready

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

### Run the pipeline on the chosen stack

Set the cloud stack active:

```shell
zenml stack set NAME_OF_STACK
```

Run the training pipeline:
```shell
python run.py --training-pipeline
```

You will notice that your pipeline run will behave differently from befeore.
Here are the broad sequence of events that just happened:

1. The user runs a pipeline on the client machine (in this case the training pipeline of the starter template).
2. The client asks the server for the stack info, which returns it with the configuration of the cloud stack.
3. Based on the stack info and pipeline specification, client builds and pushes image to the `container registry`. The image contains the environment needed to execute the pipeline and the code of the steps.
4. The client creates a run in the `orchestrator`. In this case, we are leveraging the [Skypilot](https://skypilot.readthedocs.io/) orchestrator to create a virtual machine in the cloud and run our code on it.  
5. The `orchestrator` pulls the appropriate image from the `container registry` as its executing the pipeline (each step has an image).
6. As each pipeline runs, it stores artifacts physically in the `artifact store`.
7. As each pipeline runs, it reports status back to the zenml server, and optionally queries the server for metadata.

For more detailed information on each step and additional cloud provider configurations, please refer to the [Stack deployment](../../stacks-and-components/stack-deployment/stack-deployment.md) and [Component Guide](../../stacks-and-components/component-guide/) sections of the ZenML documentation.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
