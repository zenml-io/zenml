# Team collaboration with ZenML and Google Cloud

ZenML's mission is centered on reproducible Machine Learning, with easy access to integrations for your favorite technologies. A key aspect of this mission is the ability to easily collaborate with your team across machines and environments, without sacrifices.

Collaboration with ZenML means shared access to all metadata, pipeline results, and artifacts - regardless of which team member ran the corresponding pipelines, and regardless of the environment the experiments were run in.

To achieve this, we will use Google Cloud SQL as the centralized metadata store and Google Cloud Storage as the artifact store.

## Setting up Google Cloud

### Prerequisites

This guide assumes you have access to a Google Cloud account and the Google Cloud SDK installed on all team members' machines.

#### **Suggested roles:**

* **Cloud SQL Admin** \(`roles/cloudsql.admin`\) You will need to create a Cloud SQL MySQL instance.
* **Storage Admin** \(`roles/storage.admin`\) You will need to create a bucket.

#### Helper variables

When working with the Google Cloud SDK CLI, `gcloud`, exporting a few helper variables can make life a bit easier:

* Your Google Cloud Project ID:  `export PROJECT_ID="your-projects-name"` 
* Your Google Cloud IAM user:  `export IAM_USER="your@user.id`
*  Your Google Cloud region of choice: `export REGION="europe-west1"` 
* Your Google Cloud SQL metadata instance name: `export INSTANCE_NAME="zenml-metadata"`  
* Your Google Cloud Storage artifact store bucket name: `export BUCKET_NAME="zenml-metadata"`   

#### Check your own permissions

Before we begin, you can make sure your Google Cloud User has at least the [required permissions](team-collaboration-with-zenml-and-google-cloud.md#suggested-permissions) for this tutorial:

```bash
gcloud projects get-iam-policy ${PROJECT_ID} \
    --flatten="bindings[].members" \
    --filter="bindings.members:user:${IAM_USER}"
```

### 1. Create a Google Cloud SQL MySQL instance as the metadata store

For this example, we're gonna use a small and simple MySQL instance \(`db-n1-standard-1`\) on Google Cloud SQL, without any bells and whistles. Your individual use-case might vary - [feel free to extend your own approach](https://cloud.google.com/sql/docs/mysql/create-instance#gcloud), any MySQL instance will be suitable.

**NOTE:** You do not need to use the name we chose \(`zenml-metadata`\) - feel free to pick your own.

```bash
 gcloud sql instances create ${INSTANCE_NAME} \
    --tier=db-n1-standard-1 \
    --region=${REGION}
```

### 2. Create a Google Cloud Storage bucket as the artifact store

Google Cloud Storage is one of the natively support artifact stores for ZenML. All pipeline artifacts will be persisted in this bucket, and enable cool features like caching across environments, the ability to evaluate and compare pipelines that were executed on different machines, and many others.

**NOTE:** You do not need to use the name we chose \(`zenml-metadata`\) - feel free to pick your own.

```bash
  gsutil mb -p ${PROJECT_ID} \
    -c STANDARD \
    -l ${REGION} \
    gs://${BUCKET_NAME}
```

### 3. Enable your team

Now it's time to make sure, all team members can access both the storage bucket as well as Google Cloud SQL. For that, please check the permissions for your team members Google Cloud Users. The recommended roles for your team members are:

* **Cloud SQL Client** \(`roles/cloudsql.client`\) Team members need to be able to connect to Google Cloud SQL MySQL instances.
* **Storage Admin** \(`roles/storage.admin`\) Team members need to be able to view buckets, view objects, and create objects.

## Configuring ZenML

### 1. Connect your environment to the metadata store on Google Cloud SQL

In order to successfully connect an environment to the Google Cloud SQL instance we plan on using as metadata store, it's recommended to use the Google Cloud SQL Proxy. This tutorial is going to use a Docker-based approach, but feel free to[ use other ways, if more convenient or relevant to your use-case](https://cloud.google.com/sql/docs/mysql/connect-overview).

```bash
docker run -d \
  -p 127.0.0.1:3306:3306 \
  -env TOKEN $(gcloud auth application-default print-access-token) \
  gcr.io/cloudsql-docker/gce-proxy:1.19.1 /cloud_sql_proxy \
  -instances=INSTANCE_CONNECTION_NAME=tcp:0.0.0.0:3306 \
  -token=${TOKEN}
```



