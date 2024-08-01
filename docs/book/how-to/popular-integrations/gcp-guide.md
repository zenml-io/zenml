---
description: A simple guide to quickly set up a minimal stack on GCP.
---

# Set up a minimal GCP stack

This page aims to quickly set up a minimal production stack on GCP. With just a few simple steps you will set up a service account with specifically-scoped permissions that ZenML can use to authenticate with the relevant GCP resources.

{% hint style="info" %}
Would you like to skip ahead and deploy a full GCP ZenML cloud stack already?

Check out the
[easy cloud deployment wizard](../../how-to/stack-deployment/deploy-a-cloud-stack.md),
the [easy cloud registration wizard](../../how-to/stack-deployment/register-a-cloud-stack.md),
or [the ZenML GCP Terraform module](../../how-to/stack-deployment/deploy-a-cloud-stack-with-terraform.md)
for a shortcut on how to deploy & register this stack.
{% endhint %}


{% hint style="warning" %}
While this guide focuses on Google Cloud, we are seeking contributors to create a similar guide for other cloud providers. If you are interested, please create a [pull request over on GitHub](https://github.com/zenml-io/zenml/blob/main/CONTRIBUTING.md).
{% endhint %}

### 1) Choose a GCP project

In the Google Cloud console, on the project selector page, select or [create a Google Cloud project](https://cloud.google.com/resource-manager/docs/creating-managing-projects). Make sure a billing account is attached to this project to allow the use of some APIs.

This is how you would do it from the CLI if this is preferred.

```bash
gcloud projects create <PROJECT_ID> --billing-project=<BILLING_PROJECT>
```

{% hint style="info" %}
If you don't plan to keep the resources that you create in this procedure, create a new project. After you finish these steps, you can delete the project, thereby removing all resources associated with the project.
{% endhint %}

### 2) Enable GCloud APIs

The [following APIs](https://console.cloud.google.com/flows/enableapi?apiid=cloudfunctions,cloudbuild.googleapis.com,artifactregistry.googleapis.com,run.googleapis.com,logging.googleapis.com\\\&redirect=https://cloud.google.com/functions/docs/create-deploy-gcloud&\\\_ga=2.103703808.1862683951.1694002459-205697788.1651483076&\\\_gac=1.161946062.1694011263.Cj0KCQjwxuCnBhDLARIsAB-cq1ouJZlVKAVPMsXnYrgQVF2t1Q2hUjgiHVpHXi2N0NlJvG3j3y-PPh8aAoSIEALw\\\_wcB) will need to be enabled within your chosen GCP project.

* Cloud Functions API # For the vertex orchestrator
* Cloud Run Admin API # For the vertex orchestrator
* Cloud Build API # For the container registry
* Artifact Registry API # For the container registry
* Cloud Logging API # Generally needed

### 3) Create a dedicated service account

The service account should have these following roles.

* AI Platform Service Agent
* Storage Object Admin

These roles give permissions for full CRUD on storage objects and full permissions for compute within VertexAI.

### 4) Create a JSON Key for your service account

This [json file](https://cloud.google.com/iam/docs/keys-create-delete) will allow the service account to assume the identity of this service account. You will need the filepath of the downloaded file in the next step.

```bash
export JSON_KEY_FILE_PATH=<JSON_KEY_FILE_PATH>
```

### 5) Create a Service Connector within ZenML

The service connector will allow ZenML and other ZenML components to authenticate themselves with GCP.

{% tabs %}
{% tab title="CLI" %}
```bash
zenml integration install gcp \
&& zenml service-connector register gcp_connector \
--type gcp \
--auth-method service-account \
--service_account_json=@${JSON_KEY_FILE_PATH} \
--project_id=<GCP_PROJECT_ID>
```
{% endtab %}
{% endtabs %}

### 6) Create Stack Components

#### Artifact Store

Before you run anything within the ZenML CLI, head on over to GCP and create a GCS bucket, in case you don't already have one that you can use. Once this is done, you can create the ZenML stack component as follows:

{% tabs %}
{% tab title="CLI" %}
```bash
export ARTIFACT_STORE_NAME=gcp_artifact_store

# Register the GCS artifact-store and reference the target GCS bucket
zenml artifact-store register ${ARTIFACT_STORE_NAME} --flavor gcp \
    --path=gs://<YOUR_BUCKET_NAME>

# Connect the GCS artifact-store to the target bucket via a GCP Service Connector
zenml artifact-store connect ${ARTIFACT_STORE_NAME} -i
```

{% hint style="info" %}
Head on over to our [docs](../../component-guide/artifact-stores/gcp.md) to learn more about artifact stores and how to configure them.
{% endhint %}
{% endtab %}
{% endtabs %}

#### Orchestrator

This guide will use Vertex AI as the orchestrator to run the pipelines. As a serverless service Vertex is a great choice for quick prototyping of your MLOps stack. The orchestrator can be switched out at any point in the future for a more use-case- and budget-appropriate solution.

{% tabs %}
{% tab title="CLI" %}
```bash
export ORCHESTRATOR_NAME=gcp_vertex_orchestrator

# Register the GCS artifact-store and reference the target GCS bucket
zenml orchestrator register ${ORCHESTRATOR_NAME} --flavor=vertex 
  --project=<PROJECT_NAME> --location=europe-west2

# Connect the GCS orchestrator to the target gcp project via a GCP Service Connector
zenml orchestrator connect ${ORCHESTRATOR_NAME} -i
```

{% hint style="info" %}
Head on over to our [docs](../../component-guide/orchestrators/vertex.md) to learn more about orchestrators and how to configure them.
{% endhint %}
{% endtab %}
{% endtabs %}

#### Container Registry

{% tabs %}
{% tab title="CLI" %}
```bash
export CONTAINER_REGISTRY_NAME=gcp_container_registry

zenml container-registry register ${CONTAINER_REGISTRY_NAME} --flavor=gcp --uri=<GCR-URI>

# Connect the GCS orchestrator to the target gcp project via a GCP Service Connector
zenml container-registry connect ${CONTAINER_REGISTRY_NAME} -i
```

{% hint style="info" %}
Head on over to our [docs](../../component-guide/container-registries/container-registries.md) to learn more about container registries and how to configure them.
{% endhint %}
{% endtab %}
{% endtabs %}

### 7) Create Stack

{% tabs %}
{% tab title="CLI" %}
```bash
export STACK_NAME=gcp_stack

zenml stack register ${STACK_NAME} -o ${ORCHESTRATOR_NAME} \
    -a ${ARTIFACT_STORE_NAME} -c ${CONTAINER_REGISTRY_NAME} --set
```

{% hint style="info" %}
In case you want to also add any other stack components to this stack, feel free to do so.
{% endhint %}
{% endtab %}
{% endtabs %}

## And you're already done!

Just like that, you now have a fully working GCP stack ready to go. Feel free to take it for a spin by running a pipeline on it.

## Cleanup

If you do not want to use any of the created resources in the future, simply delete the project you created.

```bash
gcloud project delete <PROJECT_ID_OR_NUMBER>
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
