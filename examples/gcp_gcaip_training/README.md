# Train easily on the cloud with one flag
In ZenML, one can configure a `TrainerStep` along with different `TrainingBackend` for different use-cases.

## Adding a training backend to a TrainerStep
The pattern to add a training backend to the trainer step is:

```python
backend = ...  # define the backend you want to use
pipeline.add_trainer(
    TrainerStep(...).with_backend(backend)
)
```

## Running on Google Cloud AI Platform
This example utilizes [Google Cloud AI Platform](https://cloud.google.com/ai-platform/docs) as the training backend to 
run the training code using GCP cloud GPU resources.

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
cd examples/gcp_gpu_training
```

Also do the following:

* [Enable billing](https://cloud.google.com/billing/docs/how-to/modify-project#enable_billing_for_a_project) in your Google Cloud Platform project.
* [Make sure you have permission locally](https://cloud.google.com/dataflow/docs/concepts/access-control) to launch a Google Cloud VM.
* Make sure you enable the following APIs:
  * Google Cloud AI Platform
  * Cloud SQL
  * Cloud Storage

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

### Create a Google Cloud Platform bucket
GCAIP uses a Google Cloud Storage bucket as a staging location for the training job. You can create a 
bucket in your project by using `gsutil`:

```bash
gsutil mb $GCP_BUCKET
```

### Create Cloud SQL Instance
The metadata store needs to be in the same GCP project as the GCP orchestrator and GCAIP Training job. An easy way to achieve 
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
This will launch a virtual machine in your GCP project that will run the entire pipeline. All steps will run on the VM, except the 
`TrainerStep` that will run as a Google Cloud AI Platform job.

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
If you are using a custom Trainer, then you need to build a new Docker image based on the ZenML Trainer 
image, and pass that into the `image` parameter in the SingleGPUTrainingGCAIPBackend. 
Find out more in [the docs](https://docs.zenml.io/backends/using-docker.html).


## Next Steps
Create your own trainers and run your own jobs! 