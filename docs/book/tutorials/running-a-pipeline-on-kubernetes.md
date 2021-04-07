# Running a pipeline on Kubernetes

Kubernetes is the clear winner of the "_container wars_", and widely offered across public cloud providers.

ZenML offers a clean and simple way to run your pipelines on any Kubernetes cluster as Jobs.

## Overview

Quite similar to the [GCP Orchestrator](https://github.com/maiot-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/tutorials/tutorials/running-a-pipeline-on-a-google-cloud-vm.md), the Kubernetes Orchestrator will create a snapshot of your local environment on the Artifact Store and create a Job on your specified Kubernetes Cluster. The Job will be using a ZenML Docker Image, load the snapshot, connect to your Metadata Store and proceed to run your pipeline.

If not specified further, all steps of your pipeline will be run on your Kubernetes cluster. However, you can mix-and-match to add even more power to your pipelines. A common scenario would be Google Cloud: pipelines are using Kubernetes as the main orchestrator, and training steps rely on [Google Cloud AI Platform](../backends/training-backends.md).

## Example: Kubernetes on GCP \(GKE\)

### Prerequisites

Architecturally, all you need to make sure of is access from the Kubernetes cluster to both your metadata and artifact store. The example below will rely on a Google Cloud Storage Bucket as Artifact Store and Google Cloud SQL as Metadata store, both within the same Google Cloud Project.

If you'd like a quick pointer on how to set up Google Cloud for ZenML, simply head on over to the setup instructions of our [Tutorial on Team Collaboration on Google Cloud](https://docs.zenml.io/tutorials/team-collaboration-with-zenml-and-google-cloud.html#setting-up-google-cloud).

Before we dive deeper, let's establish some helpers for later:

* Your Google Cloud Project ID:

  `export PROJECT_ID="your-projects-name"`

* Your Google Cloud region of choice:

  `export REGION="europe-west1"`

* Your Google Cloud SQL metadata instance name:

  `export INSTANCE_NAME="zenml-metadata"`

* Your Google Cloud Storage artifact store bucket name:

  `export BUCKET_NAME="gs://zenml-metadata-$(date +%s)"`

* Your Google Cloud Kubernetes Cluster name:

  `export CLUSTER_NAME=zenml`

* Your Google Cloud Service Account name:

  `export SERVICE_ACCOUNT_ID=zenml`

#### The cluster

Additionally, you'll require a Kubernetes cluster. It's permissions should be scoped so that it has access to other services within Google Cloud. An example cluster, with a broad range of permissions and some additional, helpful configuration, can be spun up like so:

```bash
gcloud container clusters create  ${CLUSTER_NAME}\
    --enable-intra-node-visibility \     
    --enable-ip-alias \
    --enable-stackdriver-kubernetes \
    --region=${REGION} \
    --scopes=bigquery,cloud-platform,cloud-source-repos,cloud-source-repos-ro,compute-ro,compute-rw,datastore,default,gke-default,logging-write,monitoring,monitoring-write,pubsub,service-control,service-management,sql-admin,storage-full,storage-ro,storage-rw,taskqueue,trace,userinfo-email \
    --addons=HttpLoadBalancing,HorizontalPodAutoscaling \
    --enable-network-egress-metering \
    --enable-resource-consumption-metering \
    --resource-usage-bigquery-dataset=usage_metering_dataset \
    --enable-tpu \
    --enable-network-policy \
    --enable-autoscaling \
    --max-nodes 100
```

Having that out of the way, you can conveniently use `gcloud` to create the necessary configurations on your local machine:

```bash
gcloud container clusters get-credentials ${CLUSTER_NAME} --region ${REGION}
```

#### Metadata Store connection

Another important aspect of successful pipelines on Kubernetes, as already pointed out, is a functioning connection to your Metadata Store. If you stuck to our Guide so far, you have created a [Google Cloud SQL MySQL instance](https://docs.zenml.io/tutorials/team-collaboration-with-zenml-and-google-cloud.html#create-a-google-cloud-sql-mysql-instance-as-the-metadata-store). This example will be using Google's ["Cloud SQL Proxy"](https://cloud.google.com/sql/docs/mysql/sql-proxy), a pre-built Docker image exactly for a purpose like this one.

#### Service account

A service account is advised, to facilitate the connection of the Cloud SQL Proxy to the Metadata Store. Kubernetes has a great concept for this, called Secrets. The steps are simple:

1. Create a service account:

   ```bash
   gcloud iam service-accounts create ${SERVICE_ACCOUNT_ID} \
    --description="ZenML Cloud SQL Proxy Service Account" \
    --display-name="ZenML Cloud SQL Proxy"
   ```

2. Assign the correct permissions \(in our case, **Cloud SQL Admin** \(`roles/cloudsql.admin`\)\):

   ```bash
   gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_ID}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/cloudsql.admin"
   ```

3. Creating a key file for this new service account:

   ```text
   gcloud iam service-accounts keys create key.json \
   --iam-account ${SERVICE_ACCOUNT_ID}@{PROJECT_ID}.iam.gserviceaccount.com
   ```

4. Create a Kubernetes Secret for this Service account:

   ```bash
   kubectl create secret generic zenml-cloudsql-key --from-file=key.json=key.json
   ```

#### The Kubernetes Cloud SQL Proxy service

Having the secret handled, you'll want to create a so called _Service_ in Kubernetes. This Service is using the aforementioned Google Cloud SQL Proxy to funnel all connections of your ZenML pipeline to your Metadata Store. For convenience, here's a partially finished YAML you can use to create this Service.

**NOTE:** You will have to adjust the connection string for your Google Cloud SQL Instance. Finding that connection string is easy:

```bash
gcloud sql instances describe ${INSTANCE_NAME} --flatten="connectionName"
```

The Service definition:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cloudsql
  labels:
    app: cloudsql
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cloudsql
  template:
    metadata:
      labels:
        app: cloudsql
    spec:
      containers:
      - name: cloudsql
        image: gcr.io/cloudsql-docker/gce-proxy:1.10
        command: ["/cloud_sql_proxy",
                  "-instances=INSTANCE_CONNECTION_STRING=tcp:0.0.0.0:3306",
                  "-credential_file=/secrets/cloudsql/key.json"]
        volumeMounts:
        - name: cloudsql-instance-credentials
          mountPath: /secrets/cloudsql
          readOnly: true
      volumes:
      - name: cloudsql-instance-credentials
        secret:
          secretName: zenml-cloudsql-key
---
kind: Service
apiVersion: v1
metadata:
  name: sql-proxy-service
spec:
  selector:
    app: cloudsql
  ports:
    - protocol: TCP
      port: 3306
      targetPort: 3306
```

### Running your pipeline

So far, you've created a Kubernetes Cluster, potentially a Google Cloud SQL MySQL Instance and a Google Cloud Storage Bucket, a Service Account, a Kubernetes Secret, and a Kubernetes Service. Not a bad day's of work, but now the fun part begins: Running your pipeline.

For this example, we'll use a simple one:

```python
import os

from zenml.backends.orchestrator import OrchestratorKubernetesBackend
from zenml.datasources import CSVDatasource
from zenml.metadata import MySQLMetadataStore
from zenml.pipelines import TrainingPipeline
from zenml.repo import ArtifactStore
from zenml.steps.evaluator import TFMAEvaluator
from zenml.steps.preprocesser import StandardPreprocesser
from zenml.steps.split import RandomSplit
from zenml.steps.trainer import TFFeedForwardTrainer

training_pipeline = TrainingPipeline(name='kubernetes')

# Add a datasource. This will automatically track and version it.
try:
    ds = CSVDatasource(name='Pima Indians Diabetes',
                       path='gs://zenml_quickstart/diabetes.csv')
except:
    # A small nicety for people that have ran a quickstart before :)
    from zenml.repo.repo import Repository

    repo: Repository = Repository.get_instance()
    ds = repo.get_datasource_by_name("Pima Indians Diabetes")

training_pipeline.add_datasource(ds)

# Add a split
training_pipeline.add_split(RandomSplit(
    split_map={'train': 0.7, 'eval': 0.3}))

# Add a preprocessing unit
training_pipeline.add_preprocesser(
    StandardPreprocesser(
        features=['times_pregnant', 'pgc', 'dbp', 'tst', 'insulin', 'bmi',
                  'pedigree', 'age'],
        labels=['has_diabetes'],
        overwrite={'has_diabetes': {
            'transform': [{'method': 'no_transform', 'parameters': {}}]}}
    ))
# Add a trainer
training_pipeline.add_trainer(TFFeedForwardTrainer(
    loss='binary_crossentropy',
    last_activation='sigmoid',
    output_units=1,
    metrics=['accuracy'],
    epochs=20))
# Add an evaluator
training_pipeline.add_evaluator(
    TFMAEvaluator(slices=[['has_diabetes']],
                  metrics={'has_diabetes': ['binary_crossentropy',
                                            'binary_accuracy']}))
```

It has all we need. The trusty Pima Diabetes Dataset, the Split is there, some Transforms, and a simple model.

Now, all that's left is adding your MySQL username and password, and to configure the Kubernetes backend:

```python
# Important details:
artifact_store_bucket = 'gs://rndm-strg/zenml-k8s-test/'

mysql_host = 'cloudsql'
mysql_port = 3306
mysql_db = 'zenml'
mysql_user = 'USERNAME'
mysql_pw = 'PASSWORD'

# Path to your kubernetes config:
k8s_config_path = os.path.join(os.environ["HOME"], '.kube/config')

# Run the pipeline on a Kubernetes Cluster
training_pipeline.run(
    backend=OrchestratorKubernetesBackend(
        kubernetes_config_path=k8s_config_path,
        image_pull_policy="Always"),
    metadata_store=MySQLMetadataStore(
        host=mysql_host,
        port=mysql_port,
        database=mysql_db,
        username=mysql_user,
        password=mysql_pw,
    ),
    artifact_store=ArtifactStore(artifact_store_bucket)
)
```

### Logs and next steps

Congratulations, you've successfully launched a training pipeline on Kubernetes. In the log output you'll notice a line like this:

```text
2021-01-19 15:37:55,237 — zenml.backends.orchestrator.kubernetes.orchestrator_kubernetes_backend — INFO — Created k8s Job (batch/v1): zenml-training-kubernetes-5f4b60a6-477f-435b-9b1d-cf4523873fe5
```

Now, just having a pipeline run is no fun at all, you'll probably want to check yourself, if the Job is actually launching successfully. A quick detour into Kubernetes territory is in order.

First, let's check if the job actually launches properly:

```bash
kubectl get jobs
```

Your output should look similar to this:

```text
zenml ❯❯❯ kubectl get jobs
NAME                                                             COMPLETIONS   DURATION   AGE
zenml-training-kubernetes-8627c912-95b6-409f-b4c7-563573cc1218   0/1           4s         4s
zenml-training-kubernetes-c8ef3c0d-f630-4edf-9215-7a87e05136fa   1/1           4m6s       15m
```

But, what about logs? Unfortunately, you'll have to dig a bit deeper. The way Kubernetes works, when you create a Job, that launches a so-called "Pod". The Pod does the actual computation, and therefore is the Object to reference when it comes to Logs.

Therefore, you should check your cluster's Pods:

```bash
kubectl get pods
```

... with an expected output similar to:

```text
zenml ❯❯❯ kubectl get pods
NAME                                                              READY   STATUS      RESTARTS   AGE
cloudsql-7b8b59f75b-p6sl4                                         1/1     Running     0          3d23h
zenml-training-kubernetes-8627c912-95b6-409f-b4c7-563573ccmfqzh   1/1     Running     0          32s
zenml-training-kubernetes-c8ef3c0d-f630-4edf-9215-7a87e0519g6vv   0/1     Completed   0          15m
```

Notice the Pod called `cloudsql-XXXXXXXXXX-YYYYY`? That's the Pod for the Google Cloud SQL Proxy Service, from earlier in this tutorial.

But that's not what you're looking for, you'll want to find the Pod that corresponds to the name of the Job you launched. In this example, that'd be `zenml-training-kubernetes-8627c912-95b6-409f-b4c7-563573ccmfqzh`. Let's peek at the logs:

```bash
kubectl logs -f zenml-training-kubernetes-8627c912-95b6-409f-b4c7-563573ccmfqzh
```

Notice the `-f` in there? That'll keep the command active, and new logs will keep rolling in.

Obviously, all intermediate and final results will be stored on the Artifact store, and all metadata ends up in the Metadata store. If you've followed this tutorial as well as the [Tutorial on Team Collaboration on Google Cloud](https://docs.zenml.io/tutorials/team-collaboration-with-zenml-and-google-cloud.html#setting-up-google-cloud), you can now even use your local project envirnment to compare and evaluate this pipeline.

