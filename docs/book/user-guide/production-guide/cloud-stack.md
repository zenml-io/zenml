---
description: Provision infrastructure on the cloud.
---

# Deploying a Cloud Stack

When scaling machine learning operations from a local environment to the cloud, it's essential to have a robust infrastructure that can handle the increased complexity and demands of production workloads. In order to scale to the cloud, we need to configure a basic cloud stack in ZenML. This typically consists of three key components that we have learned about in the last section:

- The [orchestrator](../../stacks-and-components/component-guide/orchestrators/) manages the workflow and execution of your pipelines.
- The [artifact store](../../stacks-and-components/component-guide/artifact-stores/) is where your pipeline artifacts, such as datasets and models, are stored.
- The [container registry](../../stacks-and-components/component-guide/container-registries/) is a storage and content delivery system that holds your Docker container images.

In this chapter, we'll walk you through the process of deploying a basic cloud stack on a public cloud provider. This will enable you to run your MLOps pipelines in a cloud environment, leveraging the scalability and robustness that cloud platforms offer.

## Deploying on a public cloud

To get a minimal cloud stack running quickly, ZenML integrates with the [mlstacks](https://mlstacks.zenml.io/getting-started/introduction) project. Before we begin, ensure you have:

- An account with your chosen cloud provider.
- The cloud provider's CLI installed and configured with the necessary permissions.
- The `zenml` CLI installed and configured on your local machine with the [mlstacks](https://mlstacks.zenml.io/getting-started/introduction) extra (i.e. `pip install "zenml[mlstacks]"`).

Then we can start deploying infrastructure (Note that from this point on, charges will be incurred on your cloud provider):

{% tabs %}
{% tab title="GCP" %}
Deploying a basic stack on GCP involves setting up a Skypilot orchestrator, a Google Cloud Storage (GCS) artifact store, and a Google Container Registry (GCR). Follow these steps to deploy your stack:

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
Deploying a basic stack on AWS involves setting up a Skypilot orchestrator, an Amazon Simple Storage Service (S3) artifact store, and an Amazon Elastic Container Registry (ECR). Follow these steps to deploy your stack:

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

### Understanding the process

You will notice that your pipeline run will behave differently from befeore.
Here are the broad sequence of events that just happened:

1. The user runs a pipeline on the client machine
2. The client asks the server for the stack info
3. Based on the stack info and pipeline specification, client builds and pushes image to the `container registry` (this is the so called build step)
4. After thats done, the client pushes the pipeline to run in the `orchestrator`. 
5. The `orchestrator` pulls the image from the `container registry` as its executing the pipeline (each step has an image)
6. As each pipeline runs, it stores artifacts physically in the `artifact store` 
7, As each pipeline runs, it reports status back to the zenml server, and it uses the metadata from the server to run the pipeline as well

After deploying your cloud stack, set it as the active stack using the `zenml stack set` command. You can then proceed to run your pipelines, confident that your cloud infrastructure is robust and ready for production. Always monitor your cloud resources and manage access carefully to ensure security and manage costs effectively.

For more detailed information on each step and additional cloud provider configurations, please refer to the [Stack deployment](../../stacks-and-components/stack-deployment/stack-deployment.md) section of the ZenML documentation.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
