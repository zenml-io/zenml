# Running a pipeline on Google Cloud VM

Not all experiments are best-suited to local execution. Sometimes, you just need that additional power of a dedicated VM in the cloud - or just the ability to close your laptop and walk off, while the experiment continues to run. ZenML, with it's strong focus on integrations, provides a convenient way to achieve this with the built-in Google Cloud VM orchestration.

An added plus to this integration is the ability to use [preemptible](https://cloud.google.com/compute/docs/instances/preemptible) instances, which is a type of instance on GCP that you can create and run at a much lower price than normal instances. Usually, preemptible instances come with a big disadvantage of being shut down at any point within 24 hours by GCP. However, most ZenML pipelines are done well before that.

To directly see the code, head over to [GitHub](https://github.com/maiot-io/zenml/tree/main/examples/gcp_orchestrated). Otherwise, follow along here.

## Prerequisites

Running workloads on Google Cloud is simple to set up. Only a few requirements need to be met:

1. You need a Google Cloud Account. If you don't have one yet, [signing up is free and gives 300$ in credits for you to spend.](https://cloud.google.com/free?hl=de) **Please note the name of your Google Cloud Project for later use.**
2. You need a [Google Cloud Storage Bucket](https://console.cloud.google.com/storage/browser) that you'll use as your [Artifact Store](../repository/artifact-store.md). **Please note the path to the bucket you want to use:** `gs://your-bucket-name/optional-subfolder`
3. You also need a [Google Cloud SQL MySQL instance](https://console.cloud.google.com/sql/instances) to be used as your [Metadata Store](../repository/metadata-store.md). **For a successful connection, four details will be required in this tutorial:** 1. The name of a database \(you're free to choose\) 2. A username 3. A corresponding password 4. The Google Cloud SQL connection name. The connection name can be found in the details of your CloudSQL instance, and it usually has the format: `PROJECT:REGION:INSTANCE_NAME`, where:
   1. `PROJECT`  is the name of your Google Cloud Project,
   2. `REGION` is the region you created your MySQL instance in,
   3. `INSTANCE_NAME` is the name you gave your MySQL instance, 
4. An authenticated, local installation of the `gcloud`[command line](https://cloud.google.com/sdk/docs/install).
5. A [local CloudSQL proxy ](https://cloud.google.com/sql/docs/mysql/sql-proxy#install)running that proxies your CloudSQL instance for use locally. 

## Getting started

This tutorial picks up where [the quickstart ends.](../steps/quickstart.md) Nevertheless, I'll walk you through a full pipeline, just to make sure nothing breaks at an unforseen stage. Feel free to [skip ahead](running-a-pipeline-on-a-google-cloud-vm.md#configure-the-orchestrator-backend) if you're already familiar with ZenML pipelines.

### Required imports

With the prerequisites in hand, we can jump straight in. First things first, let's import all we need for this tutorial, and let's create the \(for now empty\) training pipeline object.

```python
from zenml.backends.orchestrator import OrchestratorGCPBackend
from zenml.datasources import CSVDatasource
from zenml.metadata import MySQLMetadataStore
from zenml.pipelines import TrainingPipeline
from zenml.repo import ArtifactStore
from zenml.steps.evaluator import TFMAEvaluator
from zenml.steps.preprocesser import StandardPreprocesser
from zenml.steps.split import RandomSplit
from zenml.steps.trainer import TFFeedForwardTrainer

training_pipeline = TrainingPipeline(name='GCP Orchestrated')
```

### Connect your data

Having that out of the way, you'll want to connect to your data. For our example, we'll be using a medical dataset with information on diabetes rates. Feel free to use it for your tests - the supplied path will work.

And, since it's a relatively straight-forward dataset, we can already go ahead and define both a simple random split as well as a standard preprocessor for this pipeline.

```python
# Add a datasource. This will automatically track and version it.
ds = CSVDatasource(name='Pima Indians Diabetes',
                   path='gs://zenml_quickstart/diabetes.csv')
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
```

### Add a trainer

To keep this example straightforward, we'll be using one of the built-in trainers, but you can obviously swap it out for a model of your own.

```python
# Add a trainer
training_pipeline.add_trainer(TFFeedForwardTrainer(
    loss='binary_crossentropy',
    last_activation='sigmoid',
    output_units=1,
    metrics=['accuracy'],
    epochs=20))
```

### Add an evaluator

Of course, no pipeline is complete without actually evaluating the results, and we want to produce a useable model - so let's add TFMA as an evaluator.

```python
# Add an evaluator
training_pipeline.add_evaluator(
    TFMAEvaluator(slices=[['has_diabetes']],
                  metrics={'has_diabetes': ['binary_crossentropy',
                                            'binary_accuracy']}))
```

### Configure the orchestrator backend

Now, this is the heart of this tutorial. Remember the details we noted down in the [prerequisites](running-a-pipeline-on-a-google-cloud-vm.md#prerequisites) - here we'll need them.

```python
artifact_store = 'gs://your-bucket-name/optional-subfolder'
project = 'PROJECT'  # the project to launch the VM in
zone = 'europe-west1-b'  # the zone to launch the VM in
cloudsql_connection_name = 'PROJECT:REGION:INSTANCE'
mysql_db = 'DATABASE'
mysql_user = 'USERNAME'
mysql_pw = 'PASSWORD'

# Run the pipeline on a Google Cloud VM
training_pipeline.run(
    backend=OrchestratorGCPBackend(
        cloudsql_connection_name=cloudsql_connection_name,
        project=project,
        zone=zone,
    ),
    metadata_store=MySQLMetadataStore(
        host='127.0.0.1',
        port=3306,
        database=mysql_db,
        username=mysql_user,
        password=mysql_pw,
    ),
    artifact_store=ArtifactStore(artifact_store)
)
```

**Congratulation** - you've just launched a training pipeline on a Google Cloud VM. If that was your goal, you can stop here. For those who would like to dig a bit deeper, keep reading!

### How the GCP orchestrator works

The GCP orchestrator follows a simple mechanism to orchestrate the pipeline workload. The code can be found [here](https://github.com/maiot-io/zenml/blob/main/zenml/core/backends/orchestrator/gcp/orchestrator_gcp_backend.py). The logic is as follows:

* The backend zips up the repository codebase and copies the tar over to an artifact store sub-directory.
* It then launches a VM using the Google Cloud python client.
* The VM is bootstrapped with a [startup-script](https://github.com/maiot-io/zenml/blob/main/zenml/core/backends/orchestrator/gcp/startup-script.sh) that does the following:
  * Pulls the relevant docker image \(see below\).
  * Receives the [pipeline config YAML](../pipelines/what-is-a-pipeline.md) that has the path of the `tar` source-code. It uses this to download and extract the contents on a local directory. This is why the artifact store needs to be a Google Cloud bucket that is accessible to the VM.
  * Executes the pipeline with the [LocalOrchestrator](https://github.com/maiot-io/zenml/tree/main/zenml/core/backends/orchestrator/local) locally on the VM.
  * Shuts down when that process exits.

### Customize your orchestration

Every ZenML [`Pipeline`](../pipelines/what-is-a-pipeline.md) has a `run` method that takes a list of [`Backends`](../backends/what-is-a-backend.md) as input. If you pass in an [`OrchestratorBackend`](../backends/orchestrator-backends.md) , then the default local orchestrator is replaced by whatever you send in. In this case we sent in the [`OrchestratorGCPBackend`](https://github.com/maiot-io/zenml/blob/main/zenml/core/backends/orchestrator/gcp/orchestrator_gcp_backend.py) which takes certain parameters. They are:

* `cloudsql_connection_name`: The [connection name](https://cloud.google.com/sql/docs/mysql/instance-info) of the Cloud SQL instance.
* `project`: The GCP project name.
* `zone`: The GCP project zone to launch the VM in.
* `instance_name`: Name of the launched VM instance.
* `machine_type`: The [GCP machine-type](https://cloud.google.com/compute/docs/machine-types).
* `preemptible`: Whether the VM is [preemptible](https://cloud.google.com/compute/docs/instances/preemptible) or not.
* `image`: An \(optional\) Docker image with which to launch the VM. 

Note the first three are mandatory arguments and the rest are optional that have sane defaults.

### Using custom requirements

In particular interest is the `image` argument. This argument need only be used when you have custom requirements that you would like to use in your pipeline. In order to do that, the image should be based on the base ZenML image found at:

```text
http://eu.gcr.io/maiot-zenml/zenml:base-ZENML_VERSION
```

Please do not change the entrypoint of the base image and verify that your custom requirements do not override any of the default [ZenML requirements](https://github.com/maiot-io/zenml/blob/main/requirements.txt).

