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
* `environment`: The configuration of the environment in which pipeline is executed, including  details like the [Artifact Store](../repository/artifact-store.md), [Metadata Store](../repository/metadata-store.md) and the [Backends](../backends/backends-overview.md) used.
* `steps`: The steps used that define what processing the data underwent as it went through the pipeline.

The most interesting key is perhaps the last one, i.e., `steps`. Each [`Step`](../steps/creating-custom-steps.md) contains a `source` sub-key that points to a git-sha pinned version of the file in which it resides. It also contains all the parameters used in the constructors of these classes, to track them and use them later for comparability and repeatability. [Read more about steps here](../steps/creating-custom-steps.md).

### Relation to Tensorflow Extended \(TFX\) pipelines

A ZenML pipeline in the current version is a higher-level abstraction of an opinionated [TFX pipeline](https://www.tensorflow.org/tfx). ZenML steps are in turn higher-level abstractions of TFX components. 

To be clear, currently ZenML is an easier way of defining and running TFX pipelines. However, unlike TFX, ZenML treats pipelines as first-class citizens. We will elaborate more on the difference in this space, but for now if you are coming from writing your own TFX pipelines, our [quickstart](../getting-started/quickstart.md) illustrates the difference well.



