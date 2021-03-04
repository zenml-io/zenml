# Deploy easily on the cloud with one flag
In ZenML, one can configure a `DeployerStep` for different deployment strategies and targets.

## Adding a DeployerStep
The pattern to add a deployment backend to the trainer step is:

```python
pipeline.add_deployment(
    DeployerStep(...)
)
```
Deployer steps do not take any backends directly.

## Running on Google Cloud AI Platform
This example utilize [Google Cloud AI Platform](https://cloud.google.com/dataflow) as the target to deploy 
a trained model.

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
cd examples/gcp_gcaip_deployment
```

Also do the following:

* [Enable billing](https://cloud.google.com/billing/docs/how-to/modify-project#enable_billing_for_a_project) in your Google Cloud Platform project.
* [Make sure you have permission locally](https://cloud.google.com/ai-platform/prediction/docs/deploying-models) to create a Google Cloud AI Platform deployment.
* Make sure you enable the following APIs:
  * Google Cloud AI Platform
  * Cloud Storage

### Set up env variables
The `run.py` script utilizes certain environment variables for configuration. 
Here is an easy way to set it up:

```bash
export GCP_PROJECT='project_id'
export MODEL_NAME='model_name'
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json  # optional for permissions to launch dataflow jobs
```

### Run the project
Now we're ready. Execute:

```bash
python run.py
```
This will train a model locally and then deploy the trained model to Google Cloud AI Platform.

### Clean up
Delete the deployed model:

```bash
gcloud ai-platform models delete $MODEL_NAME
```
Then in the root of your repo, delete the remaining zenml references.

```python
cd ../..
rm -r .zenml
rm -r pipelines
```

## Caveats
Currently, GCAIP deployment only works for Tensorflow-based trainers.

## Next Steps
Try switching to the [Cortex](../cortex) deployer step if you'd like to deploy on a kubernetes cluster!