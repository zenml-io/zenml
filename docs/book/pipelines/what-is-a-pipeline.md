# What is a pipeline?

A ZenML pipeline is represented by a standard config written in YAML. A sample config looks like this:

```yaml
version: '1'

datasource:
  id: acaca6c4-bbbe-49a9-bf0f-4b183ee2d9fc
  name: My CSV Datasource 11379
  source: zenml.core.datasources.csv_datasource.CSVDatasource@zenml_0.0.1rc2

environment:
  artifact_store: /path/to/local_store
  backends:
    orchestrator:
      args: {}
      type: local
    processing:
      args: {}
      type: local
    training:
      args: {}
      type: local
  enable_cache: true
  metadata:
    args:
      uri: /path/to/zenml/.zenml/local_store/metadata.db
    type: sqlite
  pipeline_name: training_Experiment 1350_4c99bb8f-098d-49f9-a20d-1d37aee67d6c

steps:

  data:
    args:
      path: ...
      schema: null
    source: zenml.core.steps.data.csv_data_step.CSVDataStep@zenml_0.0.1rc2
    
  preprocessing:
    args:
      ...
    source: zenml.core.steps.preprocesser.standard_preprocesser.standard_preprocesser.StandardPreprocesser@zenml_0.0.1rc2
  
  split:
    args:
      ...
    source: zenml.core.steps.split.random_split.RandomSplit@zenml_0.0.1rc2
  
  training:
    args:
      batch_size: 8
      dropout_chance: 0.2
      epochs: 20
      hidden_activation: relu
      hidden_layers: null
      last_activation: sigmoid
      loss: binary_crossentropy
      lr: 0.001
      metrics:
      - accuracy
      output_units: 1
    source: zenml.core.steps.trainer.feedforward_trainer.FeedForwardTrainer@zenml_0.0.1rc2
  
  evaluation:
      args:
        ...
      source: zenml.core.steps.evaluator.tfma_evaluator.TFMAEvaluator@zenml_0.0.1rc2


```

The config above can be split into 4 distinct keys:

* `version`: The version of the YAML standard to maintain backwards compatibility
* `datasource`: The datasource details to represent the data flowing through the pipeline
* `environment`: The configuration of the environment in which pipeline is executed, including  details like the [Artifact Store](../repository/artifact-store.md), [Metadata Store](../repository/metadata-store.md) and the [Backends](../backends/what-is-a-backend.md) used.
* `steps`: The steps used that define what processing the data underwent as it went through the pipeline.

The most interesting key is perhaps the last one, i.e., `steps`. Each [`Step`](../steps/what-is-a-step.md) contains a `source` sub-key that points to a git-sha pinned version of the file in which it resides. It also contains all the parameters used in the constructors of these classes, to track them and use them later for comparability and repeatability. [Read more about steps here](../steps/what-is-a-step.md).

## Standard Pipelines
Currently, there are three standard types of pipelines that should be used for different use-cases for ML in production.

* [TrainingPipeline](training-pipeline.md): To train a ML model and deploy it
* [DataPipeline](data.md): To create an immutable snapshot/version of a datasource.
* [BatchInferencePipeline](batch-inference.md): To run Batch Inference with new data on a trained ML model.

## Immutability and Reusing Pipeline Logic
After pipelines are run, they are marked as being `immutable`. This  means that the internal [Steps](../steps/what-is-a-step.md) of these pipelines can no longer be changed.
However, a common pattern in Machine Learning is to re-use logical components across the entire lifecycle. And that is after all, the whole purpose of creating steps in the 
first place.

In order to re-use logic from another pipeline in ZenML, it is as simple as to execute:
```python
from zenml.core.repo.repo import Repository

# Get a reference in code to the current repo
repo = Repository()
pipeline_a = repo.get_pipeline_by_name('Pipeline A')

# Make a copy with a unique name
pipeline_b = pipeline_a.copy(new_name='Pipeline B')

# Change steps, metadata store, artifact store, backends etc freely.
```
Ensuring that run pipelines are immutable is crucial to maintain reproducibility in the ZenML design. Using the `copy()` paradigm allows 
the freedom of re-using steps with ease, and keeps reproducibility intact.

## Creating custom pipelines
ZenML is designed in a way that the starting point to use it is to [create custom `Steps`](../steps/what-is-a-step.md) and use them in the Standard 
Pipelines defined above. However, there will always be use-cases which do no match these opiniated general Standard pipelines, therefore one can always 
create custom pipelines with arbitrary Steps.

The mechanism to create a custom Pipeline will be published in more detail soon in this space. In short, it would be involve overriding the `BasePipeline` class.
However, the details of this are currently being worked out and will be made available in future releases.

If you need this functionality earlier, then ping us on our [Slack](https://zenml.io/slack-invite) or [create an issue on GitHub](https://https://github.com/maiot-io/zenml) 
so that we know about it!

## Caching
The `copy()` paradigm also helps in *re-usability* of code across pipelines. E.g. If now only the TrainerStep is changed in `pipeline_b` above, 
then the corresponding `pipeline_b` pipeline run will skip splitting, preprocessing and re-use all the artifacts already produced by `pipeline_a`. 
Read more about [caching here](reusing-artifacts.md).

## Repository functionalities
You can get all your pipelines using the [Repository](../repository/what-is-a-repository.md) class:

```python
from zenml.core.repo.repo import Repository

repo: Repository = Repository.get_instance()

# Get all names of pipelines in repo
pipeline_names = repo.get_pipeline_names()

# Load previously run pipelines
pipelines = repo.get_pipelines()

# Get pipelines by datasource
pipelines = repo.get_pipelines_by_datasource(ds)

# Get pipelines by type
train_pipelines = repo.get_pipelines_by_type(type_filter=['train'])
```

## Relation to Tensorflow Extended \(TFX\) pipelines

A ZenML pipeline in the current version is a higher-level abstraction of an opinionated [TFX pipeline](https://www.tensorflow.org/tfx). [ZenML Steps](../steps/what-is-a-step.md) are in turn higher-level abstractions of TFX components. 

To be clear, currently ZenML is an easier way of defining and running TFX pipelines. However, unlike TFX, ZenML treats pipelines as first-class citizens. We will elaborate more on the difference in this space, but for now if you are coming from writing your own TFX pipelines, our [quickstart](../getting-started/quickstart.md) illustrates the difference well.
