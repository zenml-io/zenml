# Getting started with Google Cloud

This guide will take you from the default local stack to an opinionated cloud 
stack in no time. This should help you get started with running your machine 
learning pipeline in production.

## The cloud stack

A full cloud stack will necessarily contain these five stack components:

* An **artifact store** to save all step output artifacts, in this guide we will
use a gcp bucket for this purpose
* A **metadata store** that keeps track of the relationships between artifacts, 
runs and parameters. In our case we will opt for a MySQL database on gcp
Cloud SQL.
* The **orchestrator** to run the pipelines. Here we will opt for a Vertex AI
pipelines orchestrator. This is a serverless GCP specific offering with minimal
hassle.
* A **container registry** for 
and secret manager

## Step 1/10 Set up a gcp project (Optional)

As a first step it might make sense to 
[create](https://console.cloud.google.com/projectcreate) 
a separate gcp project for your zenml resources. However, this step is 
completely optional, and you can also move forward within an existing project. 
If some resources already exist, feel free to skip the creation of the 
resources and simply export the relevant parameters for later use.


ZenML will use your project ID at a later stage to connect to some 
resources, so let's export it. You'll most probably find it right 
[here](https://console.cloud.google.com/welcome)

```bash
export PROJECT_ID=... 
```

## Step 2/10 Enable billing

Before moving on, you'll have to make sure you attach a billing account to 
your project. In case you do not have the permissions to do so, you'll have to
ask an organization administrator to do so. 
[Here](https://console.cloud.google.com/billing/projects) is the relevant 
page to do so.

## Step 3/10 Enable Vertex AI

Vertex AI pipeline lie at the heart of our gcp stack. As the orchestrator 
Vertex AI will run your pipelines and use all the other stack components. 
All you'll need to do at this stage is enable Vertex AI
[here](https://console.cloud.google.com/vertex-ai).

Once it is enabled you will see a drop down with all the regions where 
Vertex AI is available. At this point it might also make sense to make this 
decision for your ZenML Stack.

```shell
export GCP_LOCATION=...
```

## Step 4/10 Enable Secret Manager

The secret manager will be needed so that the orchestrator will have secure
access to the other resources. 
[Here](https://console.cloud.google.com/marketplace/product/google/secretmanager.googleapis.com)
is where you'll be able to enable the secret manager.

## Step 5/10 Enable Container Registry

The Vertex AI orchestrator uses Docker Images containing your pipeline code
for pipeline orchestration. For this to work you'll need to enable the gcp
docker registry 
[here](https://console.cloud.google.com/marketplace/product/google/containerregistry.googleapis.com).

In order to use the container-registry at a later point you will need to 
set the container registry uri. This is how it is usually constructed:

```bash
export CONTAINER_REGISTRY_URI=eu.gcr.io/<PROJECT_NAME> 
```

## Step 6/10 Set up Cloud Storage as Artifact Store

Storing of 
[create](https://console.cloud.google.com/storage/create-bucket)

Within the configuration of the newly created bucket you can find the 
gsutil URI which you will need at a later point.
```bash
export GSUTIL_URI=...
```

## Step 7/10 Set up Cloud SQL instance as Metadata Store

[create](https://console.cloud.google.com/sql/instances/create;engine=MySQLe)

```bash
export DB_HOST_IP=...
export DB_PORT=...
export DB_NAME=...
```

Users -> Add user account
```bash
export DB_USER=...
export DB_PWD=...

```

* Connections -> Networking
Add 0.0.0.0 to the authorized networks, thereby allowing all incoming traffic 
from everywhere

* Connections -> Security
Select **SSL Connections only** in order to encrypt all traffic with your 
database.

Now **Create Client Certificate** and download all three files. 
```bash
export SSL_CA=@</PATH/TO/DOWNLOADED/SERVER-CERT>
export SSL_CERT=@</PATH/TO/DOWNLOADED/CLIENT-CERT>
export SSL_KEY=@</PATH/TO/DOWNLOADED/CLIENT-KEY>
```


## Step 8/10 - Create a Service Account

[here](https://console.cloud.google.com/iam-admin/serviceaccounts/create)

Allow access to these roles: 
* Vertex AI Custom Code Service Agent
* Vertex AI Service Agent
* Container Registry Service Agent
* Secret Manager Admin

Give your user access to the service account. This is the service account that
will be used by the Vertex AI compute engine.

On top of this we will also need to give permissions to the service account
of the custom code workers. For this head over to your IAM 
[configurations](https://console.cloud.google.com/iam-admin/iam), click on 
**Include Google-provided role grants** on the top right and find the 
**<project_id>@gcp-sa-aiplatform-cc.iam.gserviceaccount.com** service account. 
Now give this one the **Container Registry Service Agent** role.

```bash
export SERVICE_ACCOUNT=...
```

## Step 9/10 Set Up Gcloud CLI

Install the gcloud cli on your machine. 
[Here](https://cloud.google.com/sdk/docs/install) is a guide on how to install 
it.

You will then also need to set the gcp project that you want to communicate 
with:

```bash
gcloud config set project $PROJECT_ID
```

Additionally, you will need to configure docker with the following command:

```bash
gcloud auth configure-docker
```

## Step 10/10 ZenML Stack


```bash
zenml orchestrator register vertex_orch --flavor=vertex --project=$PROJECT_ID \
      --location=$GCP_LOCATION --workload_service_account=$SERVICE_ACCOUNT
zenml secrets-manager register gcp_secrets_manager \
      --flavor=gcp_secrets_manager --project_id=$PROJECT_ID
zenml container-registry register gcp_registry --flavor=gcp \
      --uri=$CONTAINER_REGISTRY_URI
zenml artifact-store register gcp_artifact_store --flavor=gcp \
      --path=$GSUTIL_URI
zenml metadata-store register gcp_metadata_store --flavor=mysql \
      --host=$DB_HOST_IP --port=$DB_PORT --database=$DB_NAME \
      --secret=mysql_secret
zenml stack register gcp_vertex_stack -m gcp_metadata_store \
      -a gcp_artifact_store -o vertex_orch -c gcp_registry \
      -x gcp_secrets_manager --set
```

```bash
zenml secret register mysql_secret --schema=mysql \
      --user=$DB_USER --password=$DB_PWD \
      --ssl_ca=$SSL_CA --ssl_cert=$SSL_CERT --ssl_key=$SSL_KEY
```

