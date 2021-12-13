# Get in production with Kubeflow


## Pre-requisites

In order to run this example, you need to install and initialize ZenML and Airflow.
* Docker
* K3D https://k3d.io/v5.2.1/
* Kubectl

**Note:** The local Kubeflow Pipelines deployment requires more than 2 GB of RAM, so if you're running on a mac make sure to update allowed resources in the Docker Desktop preferences.

## Installation
```bash
# Install python dependencies
pip install zenml
zenml integration install kubeflow  
zenml integration install sklearn  

# pull example
zenml example pull kubeflow
cd zenml_examples/kubeflow

# Initialize a ZenML repository
git init
zenml init
```

## Running on a local Kubeflow Pipelines deployment

### Create a new Kubeflow Pipelines Stack
```bash
# register a local docker container registry
zenml container-registry register local_registry localhost:5000

zenml orchestrator register kubeflow_orchestrator kubeflow
zenml stack register local_kubeflow_stack \
    -m local_metadata_store \ 
    -a local_artifact_store \
    -o kubeflow_orchestrator \
    -c local_registry
zenml stack set local_kubeflow_stack
```

**Note:** make sure to use port 5000 here

### Deploying Kubeflow Pipelines locally

ZenML takes care of locally deploying Kubeflow Pipelines for you, all we need to do is run:

```bash
zenml stack up
```

This will setup a local Kubernetes cluster, deploy Kubeflow Pipelines and configure all necessary components so you can get started quickly.
When the setup is finished, you will see a local URL which you can access in your browser and take a look at the Kubeflow Pipelines UI.


### Run the pipeline
Running the pipeline is as simple as running the python script:

```bash
python run.py
```

This will build a docker image containing all the necessary python packages and files, push it to the local container registry and schedule a pipeline run in Kubeflow Pipelines.
Once the script is finished, you should be able to see the pipeline run [here](http://localhost:8080/#/runs).

### Clean up
Once you're done experimenting, you can delete the local kubernetes cluster and all associated resources by calling:

```bash
zenml stack down
```


## Running the same pipeline on Kubeflow Pipelines deployed to GCP

The steps from now on assume that you have a running deployment of Kubeflow Pipelines on GCP.
TODO: GCP bucket, access to container registry authorized


### Additional setup

In order to run pipelines in GCP, we need to install one additional ZenML integration:

```bash
zenml integration install gcp
```

Authorize docker to push to your GCP container registry: `gcloud auth configure-docker`

### Create a GCP Kubeflow Pipelines Stack

Replace $PATH_TO_YOUR_CONTAINER_REGISTRY and $PATH_TO_YOUR_GCP_BUCKET with actual values.

```bash
zenml container-registry register gcp_registry $PATH_TO_YOUR_CONTAINER_REGISTRY
zenml metadata register kubeflow_metadata_store kubeflow
zenml artifact register gcp_artifact_store gcp --path=$PATH_TO_YOUR_GCP_BUCKET
zenml stack register gcp_kubeflow_stack \
  -m kubeflow_metadata_store \
  -a gcp_artifact_store \
  -o kubeflow_orchestrator \
  -c gcp_registry
zenml stack set gcp_kubeflow_stack
```

### Run the pipeline

Configuring and activating the new stack is all that's necessary to switch from running your pipelines locally to running them on GCP, so you can run the pipeline as before by calling:

```bash
python run.py
```



