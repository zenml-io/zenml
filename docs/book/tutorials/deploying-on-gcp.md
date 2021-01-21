# Deploying a model to GCP

In this tutorial, we'll go through the step-by-step process of deploying a ML pipeline on the cloud, with GPU training 
enabled.

tldr; One can utilize the [GCAIPDeployer Step](../steps/deployer.md) upon executing 

```python
from zenml.core.steps.deployer.gcaip_deployer import GCAIPDeployer

training_pipeline = TrainingPipeline(name='deployed_to_gcaip')

# add steps
...

# add gcaip deployer
deployer = GCAIPDeployer(
    project_id='project_id',
    model_name='model_name',
)
training_pipeline.add_deployment(deployer)

# Run the pipeline
training_pipeline.run()
```

Detailed tutorial to follow.