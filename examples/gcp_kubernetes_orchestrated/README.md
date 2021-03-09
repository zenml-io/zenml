# Run pipelines on a kubernetes cluster
You can easily run zenml pipelines on a cloud VM instance if local compute is not enough. With this ability, it 
is simple to run on cheap preemptible/spot instances to save costs.

## Adding an orchestration backend to a pipeline
The pattern to add a backend to the pipeline is:

```python
backend = ...  # define the orchestrator backend you want to use
pipeline.run(backend=backend)  # you can also do this at construction time
```

## Running on a pipeline a Google Kubernetes Engine (GKE)
This example utilizes [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine) to launch a job on a GKE cluster, 
which then runs the pipeline specified.

### Pre-requisites
In order to run this example, you need to clone the zenml repo.

```bash
git clone https://github.com/maiot-io/zenml.git
```

Before continuing, either [install the zenml pip package](https://docs.zenml.io/getting-started/installation.html) or install it [from the cloned repo](../../zenml/README.md). 
In both cases, make sure to also install the gcp extension (e.g. with pip: `pip install zenml[gcp]`)

```
cd zenml
zenml init
cd examples/kubernetes_orchestrated
```

Also do the following:

* [Enable billing](https://cloud.google.com/billing/docs/how-to/modify-project#enable_billing_for_a_project) in your Google Cloud Platform project.
* [Make sure you have permission locally](https://cloud.google.com/compute/docs/access/iam) to launch a compute instance.

### Set up env variables
The `run.py` script utilizes certain environment variables for configuration. 
Here is an easy way to set it up:

```bash
export GCP_BUCKET="gs://mybucketname"
export GCP_PROJECT='project_id'
export GCP_REGION='my_region'export MYSQL_DB='database'
export GCP_CLOUD_SQL_INSTANCE_NAME='cloudsql_instance_name'
export MYSQL_USER='username'
export MYSQL_PWD='password'
export MYSQL_HOST='127.0.0.1'
export MYSQL_PORT=3306
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json  # optional for permissions to launch dataflow jobs
```

## Ensure that you have kubectl
This example assumes you have [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/) installed and ready 
to use. Additionally, it assumes there is a `.kube/config` configuration file in your $HOME directory. To check, try using:

```bash
kubectl version
```
which should return a result that ensures kubectl is installed on your machine.

### Create a Google Cloud Platform bucket
As the instance needs access to an artifact store, the local artifact store will not work. Instead, we can create a 
bucket and use it instead:

```bash
gsutil mb $GCP_BUCKET
```

### Create Cloud SQL Instance
The metadata store needs to be in the same GCP project as the GCP orchestrator. An easy way to achieve 
this is by simply creating a [Cloud SQL Instance](https://cloud.google.com/sql/), which is Google's managed MySQL client.

```bash
gcloud sql instances create $GCP_CLOUD_SQL_INSTANCE_NAME --tier=db-n1-standard-2 --region=$GCP_REGION
```

### Run the Cloud SQL proxy
The proxy needs to run locally for your local client to be able to access the metadata store. Download the proxy [here.](https://cloud.google.com/sql/docs/mysql/sql-proxy#linux-64-bit)

```bash
./cloud_sql_proxy -instances=$GCP_PROJECT:$GCP_REGION:$GCP_CLOUD_SQL_INSTANCE_NAME=tcp:3306 -credential_file=$GOOGLE_APPLICATION_CREDENTIALS
```

### Run the project
Now we're ready. Execute:

```bash
python run.py
```
This will launch a kubernetes job that will run the entire pipeline.

### Clean up
In order to clean up, you can delete the bucket, which also deletes the Artifact Store.

```bash
gsutil rm -r $GCP_BUCKET
```

Delete the Cloud SQL instance:

```bash
gcloud sql instances delete $GCP_CLOUD_SQL_INSTANCE_NAME 
```

Then in the root of your repo, delete the remaining zenml references.

```python
cd ../..
rm -r .zenml
rm -r pipelines
```

## Caveats
Unlike all `ProcessingBackend` and `TrainingBackend` cases, there is no need to create a custom image if you have 
any custom code in your pipeline to use this `OrchestratorBackend` (at least for the one used in this example). 
The only time you would need to use it if you use a custom dependency which is not present the standard Docker image from 
zenml.

## Next Steps
Try using other backends such as [processing backends](../gcp_dataflow_processing) for distributed preprocessing and [training backends](../gcp_gcaip_training) for 
GPU training on the cloud.