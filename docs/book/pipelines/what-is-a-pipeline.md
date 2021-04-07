# What is a pipeline?

A pipeline defines a sequence of \(usually data\) processing steps. Pipelines consist of [Steps](https://github.com/maiot-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/pipelines/steps/what-is-a-step.md) and each step is an independent entity that gets input and creates output. The output can potentially feed into other steps as inputs, and that's how the order of execution is decided.

Every pipeline step produces `Artifacts` that are stored in the [Artifact Store](../repository/artifact-store.md) and tracked by the [Metadata Store](../repository/metadata-store.md) associated with the pipeline. These artifacts can be fetched directly or via helper methods. E.g. The `view_statistics()` and `view_schema()` are helper methods to easily view the artifacts from interim steps in a pipeline.

Every pipeline has an environment in which it executes, the so called `Orchestration` environment. This is defined by the [Orchestrator Backend](../backends/orchestrator-backends.md). Read more in the [Backends docs](../backends/what-is-a-backend.md).

## Types of pipelines

In ZenML, pipelines can be `Standard` and `Custom`. In case of using the Standard pipelines, the order of the Step execution need not be defined, as these are higher-level abstractions for standard ML tasks. E.g. A [TrainingPipeline](https://github.com/maiot-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/pipelines/pipelines/training-pipeline.md) is used to run a training experiment and deploy the resulting model.

Custom pipelines however are more involved and require a more involved definition.

### Standard Pipelines

Currently, there are three standard types of pipelines that should be used for different use-cases for ML in production.

* [TrainingPipeline](https://github.com/maiot-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/pipelines/pipelines/training-pipeline.md): To train a ML model and deploy it
* [DataPipeline](data.md): To create an immutable snapshot/version of a datasource.
* [BatchInferencePipeline](batch-inference.md): To run Batch Inference with new data on a trained ML model.

### Create a custom pipeline

```text
Before creating your own pipeline, please make sure to follow the [general rules](../getting-started/creating-custom-logic.md)
for extending any first-class ZenML component.
```

ZenML is designed in a way that the starting point to use it is to [create custom `Steps`](https://github.com/maiot-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/pipelines/steps/what-is-a-step.md) and use them in the Standard Pipelines defined above. However, there will always be use-cases which do no match these opinionated general Standard pipelines, therefore one can always create custom pipelines with arbitrary Steps.

The mechanism to create a custom Pipeline will be published in more detail soon in this space. As a teaser, it will involve overriding the `BasePipeline` class. However, the details of this are currently being worked out and will be made available in future releases.

If you need this functionality earlier, then ping us on our [Slack](https://zenml.io/slack-invite) or [create an issue on GitHub](https://https://github.com/maiot-io/zenml) so that we know about it!

## Declarative Config

Regardless of type, a ZenML pipeline is represented by a declarative config written in YAML. A sample config looks like this:

```yaml
version: '1'
artifact_store: /path/to/artifact/store
backend:
  args: {}
  source: zenml.backends.orchestrator.base.orchestrator_base_backend.OrchestratorBaseBackend@zenml_0.2.0
  type: orchestrator
metadata:
  args:
    uri: /path/to/metadata.db
  type: sqlite
pipeline:
  name: training_1611737166_ea2acded-5273-4f56-969f-087f8b03d7b8
  type: training
  source: zenml.pipelines.training_pipeline.TrainingPipeline@zenml_0.2.0
  enable_cache: true

  datasource:
    id: be68f872-c90c-450b-92ee-f65463d9e1a4
    name: Pima Indians Diabetes 3
    source: zenml.datasources.csv_datasource.CSVDatasource@zenml_0.2.0

  steps:
    data:
      args:
        path: gs://zenml_quickstart/diabetes.csv
        schema: null
      source: zenml.steps.data.csv_data_step.CSVDataStep@zenml_0.2.0
    evaluator:
      args:
        metrics:
          has_diabetes:
          - binary_crossentropy
          - binary_accuracy
        slices:
        - - has_diabetes
      backend:
        args: &id001
          autoscaling_algorithm: THROUGHPUT_BASED
          disk_size_gb: 50
          image: eu.gcr.io/maiot-zenml/zenml:dataflow-0.2.0
          job_name: zen_1611737163
          machine_type: n1-standard-4
          max_num_workers: 10
          num_workers: 4
          project: core-engine
          region: europe-west1
          staging_location: gs://zenmlartifactstore/dataflow_processing/staging
          temp_location: null
        source: zenml.backends.processing.processing_dataflow_backend.ProcessingDataFlowBackend@zenml_0.2.0
        type: processing
      source: zenml.steps.evaluator.tfma_evaluator.TFMAEvaluator@zenml_0.2.0
    preprocesser:
      args:
        features:
        - times_pregnant
        - pgc
        - dbp
        - tst
        - insulin
        - bmi
        - pedigree
        - age
        labels:
        - has_diabetes
        overwrite:
          has_diabetes:
            transform:
            - method: no_transform
              parameters: {}
      backend:
        args: *id001
        source: zenml.backends.processing.processing_dataflow_backend.ProcessingDataFlowBackend@zenml_0.2.0
        type: processing
      source: zenml.steps.preprocesser.standard_preprocesser.standard_preprocesser.StandardPreprocesser@zenml_0.2.0
    split:
      args:
        split_map:
          eval: 0.3
          train: 0.7
      backend:
        args: *id001
        source: zenml.backends.processing.processing_dataflow_backend.ProcessingDataFlowBackend@zenml_0.2.0
        type: processing
      source: zenml.steps.split.random_split.RandomSplit@zenml_0.2.0
    trainer:
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
      source: zenml.steps.trainer.tensorflow_trainers.tf_ff_trainer.FeedForwardTrainer@zenml_0.2.0
```

The config above can be split into 5 distinct keys:

* `version`: The version of the YAML standard to maintain backwards compatibility.
* `artifact_store`: The path where the artifacts produced by the pipelines are stored.
* `backend`: The orchestrator [backend](../backends/what-is-a-backend.md) for the pipeline.
* `metadata`: The metadata store config to store information of pipeline runs.
* `pipeline`: A global key that contains information regarding the pipeline run itself:
  * `source`: Path to pipeline code source code.
  * `args`: Individual args of the pipeline like `name` etc.
  * `datasource`: Details of the [datasource](../datasources/what-is-a-datasource.md) used in the pipeline. 
  * `steps:`: Details of each [step](https://github.com/maiot-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/pipelines/steps/what-is-a-step.md) used in the pipeline.

## Immutability and Reusing Pipeline Logic

After pipelines are run, they are marked as being `immutable`. This means that the internal [Steps](https://github.com/maiot-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/pipelines/steps/what-is-a-step.md) of these pipelines can no longer be changed. However, a common pattern in Machine Learning is to re-use logical components across the entire lifecycle. And that is after all, the whole purpose of creating steps in the first place.

In order to re-use logic from another pipeline in ZenML, it is as simple as to execute:

```python
from zenml.repo.repo import Repository

# Get a reference in code to the current repo
repo = Repository()
pipeline_a = repo.get_pipeline_by_name('Pipeline A')

# Make a copy with a unique name
pipeline_b = pipeline_a.copy(new_name='Pipeline B')

# Change steps, metadata store, artifact store, backends etc freely.
```

Ensuring that run pipelines are immutable is crucial to maintain reproducibility in the ZenML design. Using the `copy()` paradigm allows the freedom of re-using steps with ease, and keeps reproducibility intact.

## Caching

The `copy()` paradigm also helps in _re-usability_ of code across pipelines. E.g. If now only the TrainerStep is changed in `pipeline_b` above, then the corresponding `pipeline_b` pipeline run will skip splitting, preprocessing and re-use all the artifacts already produced by `pipeline_a`. Read more about [caching here](https://github.com/maiot-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/pipelines/benefits/reusing-artifacts.md).

## Repository functionalities

You can get all your pipelines using the [Repository](../repository/what-is-a-repository.md) class:

```python
from zenml.repo import Repository

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

A ZenML pipeline in the current version is a higher-level abstraction of an opinionated [TFX pipeline](https://www.tensorflow.org/tfx). [ZenML Steps](https://github.com/maiot-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/pipelines/steps/what-is-a-step.md) are in turn higher-level abstractions of TFX components.

To be clear, currently ZenML is an easier way of defining and running TFX pipelines. However, unlike TFX, ZenML treats pipelines as first-class citizens. We will elaborate more on the difference in this space, but for now if you are coming from writing your own TFX pipelines, our [quickstart](../steps/quickstart.md) illustrates the difference well.

