# Switching backends
One of the most powerful things in ZenML is the notion of backends. This is a showcase of different backends and how 
to use them together in various use-cases.

## Pre-requisites
In order to run this example, you need to install and initialize ZenML

```bash
pip install "zenml[gcp]"
zenml example pull backends
cd zenml_examples/backends
git init
zenml init
```

You also need to enable the following GCP services (and enable billing).

* Google Compute VM
* Google Cloud AI Platform
* Google Cloud Storage
* Google Cloud Dataflow
* Google CloudSQL

You also need to create a google service account that has permission to read/write to all of the above services and 
specify that in your `GOOGLE_APPLICATION_CREDENTIALS` env variable (see below).

## Run the project
Now we're ready. First fill in the env variables required. 

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/creds
export GCP_BUCKET=""
export GCP_PROJECT=""
export GCP_REGION=""
export GCP_CLOUD_SQL_INSTANCE_NAME=""
export MODEL_NAME=""
export CORTEX_ENV=""
export MYSQL_DB=""
export MYSQL_USER=""
export MYSQL_PWD=""
export MYSQL_PORT=""
export MYSQL_HOST=""
```

Then run the jupyter notebook:

```bash
jupyter notebook
```

### Clean up
In order to clean up, in the root of your repo, delete the remaining zenml references.

```python
rm -r .zenml
rm -r pipelines
```

You can also delete your GCP project to clean up all resources associated with the pipeline runs.

## Caveats
This example is still WIP

## Next Steps
