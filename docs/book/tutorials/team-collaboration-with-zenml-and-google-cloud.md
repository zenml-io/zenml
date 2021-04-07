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

#### **Helper variables**

When working with the Google Cloud SDK CLI, `gcloud`, exporting a few helper variables can make life a bit easier:

* Your Google Cloud Project ID:

  `export PROJECT_ID="your-projects-name"`

* Your Google Cloud IAM user:

  `export IAM_USER="your@user.id`

* Your Google Cloud region of choice:

  `export REGION="europe-west1"`

* Your Google Cloud SQL metadata instance name:

  `export INSTANCE_NAME="zenml-metadata"`

* Your Google Cloud Storage artifact store bucket name:

  `export BUCKET_NAME="gs://zenml-metadata-$(date +%s)"`

  **NOTE:** The bucket name in this example features an epoch timestamp to ensure uniqueness.

#### **Check your own permissions**

Before we begin, you can make sure your Google Cloud User has at least the required permissions for this tutorial:

```bash
gcloud projects get-iam-policy ${PROJECT_ID} \
    --flatten="bindings[].members" \
    --filter="bindings.members:user:${IAM_USER}"
```

### 1. Create a Google Cloud SQL MySQL instance as the metadata store

For this example, we're gonna use a small and simple MySQL instance \(`db-n1-standard-1`\) on Google Cloud SQL, without any bells and whistles. Your individual use-case might vary - [feel free to extend your own approach](https://cloud.google.com/sql/docs/mysql/create-instance#gcloud), any MySQL instance will be suitable.‌

**NOTE:** You do not need to use the name we chose \(`zenml-metadata`\) - feel free to pick your own.

```bash
 gcloud sql instances create ${INSTANCE_NAME} \
    --tier=db-n1-standard-1 \
    --region=${REGION}
```

### 2. Create a Google Cloud Storage bucket as the artifact store

Google Cloud Storage is one of the natively support artifact stores for ZenML. All pipeline artifacts will be persisted in this bucket, and enable cool features like [caching](https://github.com/maiot-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/tutorials/benefits/reusing-artifacts.md) across environments, the ability to evaluate and compare pipelines that were executed on different machines, and many others.

**NOTE:** You do not need to use the name we chose \(`zenml-metadata`\) - feel free to pick your own.

```bash
  gsutil mb -p ${PROJECT_ID} \
    -c STANDARD \
    -l ${REGION} \
    ${BUCKET_NAME}
```

### 3. Enable your team

Now it's time to make sure, all team members can access both the storage bucket as well as Google Cloud SQL. For that, please check the permissions for your team members Google Cloud Users.

#### **Recommended permission**

The recommended roles for your team members are:

* **Cloud SQL Client** \(`roles/cloudsql.client`\) Team members need to be able to connect to Google Cloud SQL MySQL instances.
* **Storage Admin** \(`roles/storage.admin`\) Team members need to be able to view buckets, view objects, and create objects.

## Configuring ZenML

After successfully setting up a Google Cloud SQL instance for your metadata tracking and a Google Cloud Storage bucket for your artifact store you're ready to configure ZenML. The following steps should be repeated on all team members intended to collaborate on a project.

### 0. Initialize ZenML

As a precursor, this tutorial assumes you have successfully initialized ZenML in a project of yours. As a reminder, initializing is as easy running the following command in a `git`-backed folder:

```bash
zenml init
```

### 1. Connect your environment to the metadata store on Google Cloud SQL

In order to successfully connect an environment to the Google Cloud SQL instance we plan on using as metadata store, it's recommended to use the Google Cloud SQL Proxy. This tutorial is going to use a Docker-based approach, but feel free to [use other ways, if more convenient or relevant to your use-case](https://cloud.google.com/sql/docs/mysql/connect-overview).

```bash
docker run -d \
  -p 127.0.0.1:3306:3306 \
  -env TOKEN $(gcloud auth application-default print-access-token) \
  gcr.io/cloudsql-docker/gce-proxy:1.19.1 /cloud_sql_proxy \
  -instances=$(gcloud sql instances describe ${INSTANCE_NAME} --flatten="connectionName" | grep -v '^-')=tcp:0.0.0.0:3306 \
  -token=${TOKEN}
```

This will launch a docker container acting as a secure proxy to your metadata MySQL instance in Google Cloud. It's using token-based authentication, so no permanent credentials need to be maintained.

Your metadata MySQL instance will be accessible on `127.0.0.1` via port `3306` .

### 2. Configure the metadata and artifact store

Now, all that's left is configuring ZenML with your cloud-based metadata and artifact store for your project. All following pipelines will use them automatically, and all other connected team members will have access to results, artifacts, and other metadata.

#### **Metadata Store**

Now you'll need a MySQL user with its corresponding password and a database name. If the database does not exist and the user has sufficient MySQL permissions, a database with this name will be created automatically.↩

```bash
zenml config metadata set mysql \
    --host 127.0.0.1 \ 
    --port 3306 \
    --username USER \
    --passwd PASSWD \
    --database DATABASE
```

#### **Artifact Store**

The bucket created earlier will now serve as the artifact store for all future experiments.

```bash
zenml config artifacts set ${BUCKET_NAME}
```

‌

### 3. Repeat for team members

To get everyone on board, simply repeat the configuration steps 0, 1, and 2 for all team members. Make sure the Google Cloud User permissions are in line with our recommended roles, as missing permissions can be a common point of failure.

