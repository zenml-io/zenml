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

### Pre-requisites
In order to run this example, you need to clone the zenml repo.

```bash
git clone https://github.com/maiot-io/zenml.git
cd zenml/examples/distributed_processing
```
Also do the following:

* [Enable billing](https://cloud.google.com/billing/docs/how-to/modify-project#enable_billing_for_a_project) in your Google Cloud Platform project.
* [Make sure you have permission locally](https://cloud.google.com/dataflow/docs/concepts/access-control) to launch dataflow jobs, whether through service account or default credentials.

### Create a Google Cloud Platform bucket
Dataflow uses a Google Cloud Storage bucket as a staging location for the distributed job. You can create a 
bucket in your project by using `gsutil`:

```bash
export GCP_BUCKET="gs://mybucketname"
export GCP_PROJECT='project_id'
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json  # optional for permissions to launch dataflow jobs
gsutil mb $GCP_BUCKET
```

### Run the project
Now we're ready. Execute:

```bash
python run.py
```
This might take a while (~30 mins) as almost every step in the pipeline will now be a dataflow job. While this may 
seem a long amount of time for such a small amount of data, it will pay off on bigger datasets as most of the time is 
building up and tearing down the job.

### Clean up
In order to clean up, you can delete the bucket, which also deletes the Artifact Store.

```bash
gsutil rm -r $GCP_BUCKET
```

Then in the root of your repo, delete the remaining zenml references.

```python
cd ../..
rm -r .zenml
rm -r pipelines
```

## Next Steps
You can see how ZenML makes it easy to do distributed processing. But this is just scratching the service. You 
can combine different `ProcessingBackends` with certain [TrainingBackends](../gcp_trained/README.md) to leverage 
even more cloud power such as GPUs.