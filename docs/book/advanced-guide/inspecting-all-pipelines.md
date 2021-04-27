---
description: Pipelines are your experiments
---

# Inspecting all pipelines in a repository

All **pipelines** within a ZenML **repository** are tracked centrally. In order to access information about your **ZenML repository** in code, you need to access the **ZenML** [Repository instance](../api-reference/zenml/zenml.repo.md#zenml-repo-package). This object is a Singleton and can be fetched any time from within your Python code simply by executing:

```python
from zenml.repo import Repository

# We recommend to add the type hint for auto-completion in your IDE/Notebook
repo: Repository = Repository.get_instance()
```

Now the `repo` object can be used to fetch all pipelines:

```python
# Get all pipelines
pipelines = repo.get_pipelines()  # returns a list of BasePipeline sub-classed objects
```

Depending on the type of the pipeline, you can then use its functions to inspect the pipeline, so for example to evaluate it or see its statistics.

If you are looking for a particular pipeline, there are more refined functions:

```python
# Get all names of pipelines
names = get_pipeline_names()

# Get pipeline by name
pipeline = get_pipeline_by_name(name='Experiment 1')

# Get pipeline by type (Each pipeline has a PIPELINE_TYPE defined as a string)
pipelines = get_pipelines_by_type(type_filter=['training'])

# Get pipeline by datasource
datasources = repo.get_datasources()
pipelines = repo.get_pipelines_by_datasource(datasources[0])
```

Using these commands, one can always look back at what pipelines have been registered and run in this repository.

It is important to note that most of the methods listed above involve parsing the [config YAML files](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/pipelines/what-is-a-pipeline.html) in your [Pipelines Directory](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/repository/pipeline-directory.html). Therefore, by changing the pipelines directory or manipulating it, you may lose a lot of valuable information regarding how the repository developed over time.

## Pipeline Properties

Each pipeline has an associated [metadata store](../core-concepts.md#metadata-store), [artifact store](../core-concepts.md#artifact-store) and `step_config`. The `step_config` is a dictionary that defines which [steps](../core-concepts.md#steps) are running in the pipeline.

In order to see the status of a pipeline:

```python
pipeline.get_status()
```

This queries the associated `metadata_store`, and returns either `NotStarted`, `Suceeded` , `Running` or `Failed` depending on the status of the pipeline.

Apart from the status, pipelines can have additional properties and helper functions that one can use to inspect it closely. For example, a `TrainingPipeline` has the `get_hyperparameters()` method to return the hyper-parameters used in the preprocesser and trainer steps.

Regardless of type, a **ZenML** pipeline is represented by a declarative config written in YAML. A sample config looks like this:

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

* `version`: The version of the YAML standard to maintain backward compatibility.
* `artifact_store`: The path where the artifacts produced by the pipelines are stored.
* `backend`: The orchestrator [backend]() for the pipeline.
* `metadata`: The metadata store config to store information of pipeline runs.
* `pipeline`: A global key that contains information regarding the pipeline run itself:
  * `source`: Path to pipeline code source code.
  * `args`: Individual args of the pipeline like `name` etc.
  * `datasource`: Details of the [datasource](../starter-guide/datasource.md) used in the pipeline.
  * `steps:`: Details of each [step](https://github.com/maiot-io/zenml/tree/beef951a0f0f146c6f8e16e4ad759262acbcdfdd/docs/book/api-reference/zenml/zenml.steps) used in the pipeline.

## Manipulating a pipeline after it has been run

After pipelines are run, they are marked as being `immutable`. This means that the internal [Steps](https://github.com/maiot-io/zenml/tree/beef951a0f0f146c6f8e16e4ad759262acbcdfdd/docs/book/api-reference/zenml/zenml.steps) of these pipelines can no longer be changed. However, a common pattern in Machine Learning is to re-use logical components across the entire lifecycle. And that is, after all, the whole purpose of creating steps in the first place.

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

Ensuring that run pipelines are immutable is crucial to maintain reproducibility in the ZenML design. Using the `copy()` paradigm allows the freedom of re-using steps with ease and keeps reproducibility intact.

## Caching

The `copy()` paradigm also helps in the _**reusability**_ ****of code across pipelines. E.g. If now only the `TrainerStep` is changed in `pipeline_b` above, then the corresponding `pipeline_b` pipeline run will skip splitting, preprocessing, and re-use all the artifacts already produced by `pipeline_a`.

