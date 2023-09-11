# Quickly setting up a minimal Stack on GCP

This page will serve as a simple guide to quickly set up a minimal stack on 
gcp. 

1) Choose a GCP project
In the Google Cloud console, on the project selector page, select or [create 
a Google Cloud project](https://cloud.google.com/resource-manager/docs/creating-managing-projects).

{% hint style="info" %}
If you don't plan to keep the resources that you create in this procedure, 
create a project instead of selecting an existing project. After you finish
these steps, you can delete the project, removing all resources associated 
with the project.
{% endhint %}

2) [Enable GCloud APIs](https://console.cloud.google.com/flows/enableapi?apiid=cloudfunctions,cloudbuild.googleapis.com,artifactregistry.googleapis.com,run.googleapis.com,logging.googleapis.com&redirect=https://cloud.google.com/functions/docs/create-deploy-gcloud&_ga=2.103703808.1862683951.1694002459-205697788.1651483076&_gac=1.161946062.1694011263.Cj0KCQjwxuCnBhDLARIsAB-cq1ouJZlVKAVPMsXnYrgQVF2t1Q2hUjgiHVpHXi2N0NlJvG3j3y-PPh8aAoSIEALw_wcB)
The following APIs will need to be enabled within your chosen gcp project.
* Cloud Functions API
* Cloud Build API
* Artifact Registry API
* Cloud Run Admin API
* Cloud Logging API

3) Create a service account with the necessary roles.
The following roles give the service account permissions for full crud on 
storage objects and full permissions for compute within vertex.
* AI Platform Service Agent
* Storage Object Admin


4) Create a JSON Key for your service account.



5) Create a Service Connector in ZenML
```bash
zenml integration install gcp \
&& zenml service-connector register gcp_connector \
--type gcp \
--auth-method service-account \
--service_account_json=@<FILE_PATH> \
--project_id=<GCP_PROJECT_ID>
```
6) Create Stack Components
### Artifact Store

Before you run anything within the zenml CLI, head on over to gcp and create a 
gcs bucket if you don't have one that you can use. Once this is done, you can 
create the zenml stack component as follows:

```bash
export ARTIFACT_STORE_NAME=gcp_artifact_store

# Register the GCS artifact-store and reference the target GCS bucket
zenml artifact-store register ${ARTIFACT_STORE_NAME} --flavor gcp \
    --path='gs://<YOUR-BUCKET>'

# Connect the GCS artifact-store to the target bucket via a GCP Service Connector
zenml artifact-store connect ${ARTIFACT_STORE_NAME} -i
```

{% hint style="info" %}
Head on over to our [docs](../../component-guide/artifact-stores/gcp) to learn 
more.
{% endhint %}


### Orchestrator

```bash
export ORCHESTRATOR_NAME=gcp_vertex_orchestrator

# Register the GCS artifact-store and reference the target GCS bucket
zenml orchestrator register ${ORCHESTRATOR_NAME} --flavor=vertex 
  --project=<PROJECT_NAME> --location=europe-west2

# Connect the GCS orchestrator to the target gcp project via a GCP Service Connector
zenml orchestrator connect ${ORCHESTRATOR_NAME} -i
```

{% hint style="info" %}
Head on over to our [docs](../../component-guide/orchestrators/vertex.md) to 
learn more.
{% endhint %}

### Container Registry

```bash
export CONTAINER_REGISTRY_NAME=gcp_container_registry

zenml container-registry register ${CONTAINER_REGISTRY_NAME} --flavor=gcp --uri=<GCR-URI>

# Connect the GCS orchestrator to the target gcp project via a GCP Service Connector
zenml container-registry connect ${CONTAINER_REGISTRY_NAME} -i
```

{% hint style="info" %}
Head on over to our [docs](../../component-guide/container-registries/gcp.md)
to learn more.
{% endhint %}


7) Create Stack

```bash
export STACK_NAME=gcp_stack

zenml stack register ${STACK_NAME} -o ${ORCHESTRATOR_NAME} \
    -a ${ARTIFACT_STORE_NAME} -c ${CONTAINER_REGISTRY_NAME} --set
```

{% hint style="info" %}
In case you want to also add any other stack components to this stack, feel free
to do so.
{% endhint %}

## Finished

Just like that, you now have a fully working GCP stack ready to go. Feel free to
take it for a spin with a pipeline run.
