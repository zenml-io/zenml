# Crunch through big data with distributed processing backends

In ZenML, it is almost trivial to distribute certain `Steps` in a pipeline in cases where large 
datasets are involved. All `Steps` within a pipeline take as input a `ProcessingBackend`.

## Adding a backend to a step
The pattern to add a backend to the step is:

```python
backend = ...  # define the backend you want to use
pipeline.add_step(
    Step(...).with_backend(backend)
)
```

## Running on Google Cloud Platform and Dataflow
This example utilize [Google Cloud Dataflow](https://cloud.google.com/dataflow) as the backend to 
distribute certain Steps in the quickstart pipeline example. In order to run, follow these steps:

### Set up env variables
The `run.py` script utilizes certain environment variables for configuration. 
Here is an easy way to set it up:

```bash
export GCP_PROJECT='project_id'
export STAGING_LOCATION='gs://somebucket/path/'  # 
export MYSQL_DB='database'
export MYSQL_USER='username'
export MYSQL_PWD='password'
export MYSQL_HOST='127.0.0.1'
export MYSQL_PORT=3306
```