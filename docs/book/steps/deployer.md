# Deployer
The deployer is responsible for serving a trained model to an endpoint. It can be added to a `TrainingPipeline` through 
the `add_deployment()` method.

## Standard Deployers
There are some standard deployers built-in to ZenML for common deployment scenarios.

### GCAIPDeployer
Deploys the model directly to a [Google Cloud AI Platform](https://cloud.google.com/ai-platform/prediction/docs) end-point.

```python
from zenml.steps.deployer import GCAIPDeployer

pipeline.add_deployment(GCAIPDeployer(
    project_id='project_id',
    model_name='model_name',
))
```

```{warning}
Currently, the GCAIPDeployer only works with Trainers fully implementing the `TFBaseTrainerStep` interface. An example is the standard `tf_ff_trainer.FeedForwardTrainer` step.
```

#### How to make a request to your served model

Google Cloud AI Platform is using [TFServing](https://www.tensorflow.org/tfx/guide/serving) under-the-hood. TFServing has [defined standards](https://www.tensorflow.org/tfx/serving/api_docs/cc/) 
on how to communicate with a model.

A good example to request predictions from TFServing models can be found [here](https://www.tensorflow.org/tfx/tutorials/serving/rest_simple).

## Create custom deployer
The mechanism to create a custom Deployer will be published in more detail soon in this space.
However, the details of this are currently being worked out and will be made available in future releases.

If you need this functionality earlier, then ping us on our [Slack](https://zenml.io/slack-invite) or 
[create an issue on GitHub](https://https://github.com/maiot-io/zenml) so that we know about it!

## Downloading a trained model
The model will be present in the `TrainerStep` artifacts directory.
You can retrieve this URI directly from a pipeline by executing:

```python
pipeline.get_artifacts_uri_by_component('Trainer')
```