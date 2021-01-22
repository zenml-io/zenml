# Training with GPUs on the Cloud

In this tutorial, we'll go through the step-by-step process of deploying a ML pipeline on the cloud, with GPU training 
enabled.


tldr; One can utilize the [GCAIP Training Backend](../backends/training-backends.md).

```python
from zenml.core.backends.training.training_gcaip_backend import \
    SingleGPUTrainingGCAIPBackend

training_pipeline = TrainingPipeline(name='trained_gcaip')

# add steps
...

# configure steps
training_backend = SingleGPUTrainingGCAIPBackend(
    project='project_name',
    job_dir='gs://my_bucket/path')

# Run the pipeline
training_pipeline.run(
    backends=[training_backend],
    ...
)
```

Full code example can be found [here](https://github.com/maiot-io/zenml/blob/main/examples/gcp_trained/run.py)

Detailed tutorial to follow..

