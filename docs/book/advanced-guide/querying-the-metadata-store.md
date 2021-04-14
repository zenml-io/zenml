---
description: Form a complete picture of your ML metadata and artifacts.
---

# The metadata and artifact stores

In **ZenML**, a **pipeline** refers to a sequence of **steps** which represent independent entities that gets a certain set of inputs and creates the corresponding outputs as **artifacts**. These output **artifacts** can potentially be fed into other **steps** as inputs, and that’s how the order of execution is decided.

Each **artifact** that is produced along the way is stored in an **artifact store** and the corresponding execution is tracked by a **metadata store** associated with the **pipeline**. These artifacts can be fetched directly or via helper methods. For instance in a training pipeline,`view_statistics()` and `view_schema()` can be used as helper methods to easily view the artifacts from interim steps in a **pipeline**.

Finally, **ZenML** already natively separates configuration from code in its design. That means that every **step** in a **pipeline** has its parameters tracked and stored in the **declarative config file** in the selected **pipelines directory**. Therefore, pulling a pipeline and running it in another environment not only ensures that the code will be the same, but also the configuration.

## Configuring default metadata and artifact stores

By default, both will point to a sub folder of your local `.zenml` directory, which is created when you run `zenml init`. It’ll contain both the Metadata Store \(default: SQLite\) as well as the Artifact Store \(default: local folder in the zenml repo\).

The Metadata Store can be simply configured to use any MySQL server \(=&gt;5.6\):

```bash
zenml config metadata set mysql \
    --host="127.0.0.1" \ 
    --port="3306" \
    --username="USER" \
    --password="PASSWD" \
    --database="DATABASE"
```

The Artifact Store can be a local filesystem path or a bucket path \(current support for GCP and AWS\).

```bash
zenml config artifacts set "gs://your-bucket/sub/dir"
```

In Python, the `ArtifactStore` and `MetadataStore` classes can be used to override the default stores set above.

## How metadata is stored

ZenML uses Google’s [ML Metadata](https://github.com/google/ml-metadata) under-the-hood to automatically track all metadata produced by ZenML pipelines. ML Metadata standardizes metadata tracking and makes it easy to keep track of iterative experimentation as it happens. This not only helps in post-training workflows to [compare results](../starter-guide/post-training.md) as experiments progress but also has the added advantage of leveraging **caching** of pipeline steps.

All parameters of every ZenML step are persisted in the **Metadata Store** and also in the [declarative pipeline configs](inspecting-all-pipelines.md#pipeline-properties). In the config, they can be seen quite easily in the `steps` key. Here is a sample stemming from this Python step:

```python
training_pipeline.add_trainer(TrainerStep(
    batch_size=1,
    dropout_chance=0,
    epochs=1,
    hidden_activation="relu",
    hidden_layers=None,
    last_activation="sigmoid",
    loss="mse",
    lr=0.01,
    metrics=None,
    output_units=1,
))
```

That translates to the following config:

```yaml
steps: ...
  trainer:
    args:
      batch_size: 1
      dropout_chance: 0.2
      epochs: 1
      hidden_activation: relu
      hidden_layers: null
      last_activation: sigmoid
      loss: mse
      lr: 0.001
      metrics: null
      output_units: 1
    source: ...
```

{% hint style="info" %}
Under-the-hood, these parameters are also captured as [ExecutionParameters](https://www.tensorflow.org/tfx/api_docs/python/tfx/types/component_spec/ExecutionParameter) in [TFX components](https://www.tensorflow.org/tfx/api_docs/python/tfx/components), therefore they are directly inserted into the `Execution` table of the MLMetadata store.
{% endhint %}

The `args` key represents all the parameters captured and persisted.

For most use-cases, ZenML exposes native interfaces to fetch these parameters after a pipeline has been run successfully. E.g. the `repo.compare_training_runs()` method compares all pipelines in a [Repository](../api-reference/zenml/zenml.repo.md) and extensively uses the ML Metadata store to spin up a visualization of comparison of training pipeline results.

However, if users would like direct access to the store, they can easily use the ML Metadata Python library to quickly access their parameters. To understand more about how Execution Parameters and ML Metadata work please refer to the [TFX docs](https://www.tensorflow.org/tfx/guide/mlmd).

## How to specify what to track

As all steps are persisted in the same pattern show above, it is very simple to track any metadata you desire. Whenever creating a step, simply add the parameters you want to track as **kwargs** \(key-worded parameters\) in your Step `__init__()` method \(i.e. the constructor\) and then pass the exact same parameters in the `super()` call.

### Example:

```python
class MyTrainer(BaseTrainerStep):

def __init__(self,
             arg_1: int = 8,
             arg_2: float = 0.001,
             arg_3: str = 'mse',
             **kwargs):

    # Pass the exact same parameters as the signature down with the **kwargs dict
    super(BaseTrainerStep, self).__init__(
        arg_1=arg_1,
        arg_2=arg_2,
        arg_3=arg_3,
        **kwargs
    )
```

{% hint style="info" %}
For now, only **primitive types** are supported for tracking. You cannot track any arbitrary python object. Please ensure that only primitive types \(int, string, float etc\) are used in your Step constructors.As 
{% endhint %}

As long as the above pattern is followed, any primitive type can be tracked centrally with ZenML. As a note, while all steps are base classes of `BaseStep` , for specific step types other base classes are available. For example, if creating a preprocessing step, inherit from the `BasePreprocesserStep` step and if  trainer step the `BaseTrainerStep` or even further one level down to the `TFBaseTrainerStep` and `TorchBaseTrainerStep`. To see all the step interfaces check out the [steps module of ZenML](../api-reference/zenml/zenml.steps/#zenml-steps-package).

## Reusing Artifacts with Caching

Caching is an important mechanism for ZenML, which not only speeds up ML development, but also allows for re-usability of interim ML artifacts inevitably produced in the experimentation stage of training an ML model.

### The tremendous benefits of reusing artifacts

Whenever, a [pipeline](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/pipelines/what-is-a-pipeline.html) is run in the same repository, ZenML tracks all [Steps](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/steps/what-is-a-step.html) executed in the repository. The outputs of these steps are stored as they are computed in the [Metadata](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/repository/metadata-store.html) and [Artifact](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/repository/artifact-store.html) Stores. Whenever another pipeline is run afterwards that has the same Step configurations of a previously run pipeline, ZenML simply uses the previously computed output to **warm start** the pipeline, rather than recomputing the output.

This not only makes each subsequent run potentially much faster but also saves on computing cost. With ZenML, it is possible to [preprocess millions of datapoints](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/tutorials/building-a-classifier-on-33m-samples.html). Imagine having to re-compute this each time an experiment is run, even if it is a small change to a hyper-parameter of the TrainerStep.

This is usually solved by creating snapshots of preprocessed data unfortunately stored in random arbitrary places. In the worst case in local folders, and in the best case in some form of Cloud Storage but with a manually defined order. These have the following disadvantages:

* Data might get lost or corrupted
* Data might not be easy to share across teams or environments
* Data can be manipulated unexpectedly and transparently without anyone knowing.

With ZenML, all of this is taken care of in the background. Immutable snapshots of interim artifacts are stored in the [Artifact Store](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/repository/artifact-store.html) and stored for quick reference in the [Metadata Store](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/repository/metadata-store.html). Therefore, as long as these remain intact, data cannot be lost, corrupted or manipulated in any way unexpectedly. Also, setting up a [collaborative environment with ZenML](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/repository/team-collaboration-with-zenml.html) ensures that this data is accessible to everyone and is consumed natively by all ZenML steps with ease.

{% hint style="warning" %}
Caching only works across pipelines in the same [artifact store](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/repository/artifact-store.html) and same [metadata store](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/repository/metadata-store.html). Please make sure to put all related pipelines in the same artifact and metadata store to leverage the advantages of caching
{% endhint %}

### Example

Create and run the first pipeline:

```python
training_pipeline = TrainingPipeline(name='Pipeline A')

# create the actual pipeline

training_pipeline.run()
```

Then get the pipeline:

```python
from zenml.repo import Repository

# Get a reference in code to the current repo
repo = Repository()
pipeline_a = repo.get_pipeline_by_name('Pipeline A')
```

Create a new pipeline and change one step

```python
pipeline_b = pipeline_a.copy('Pipeline B')  # pipeline_a itself is immutable
pipeline_b.add_trainer(...)  # change trainer step
pipeline_b.run()
```

In the above example, if there is a shared Metadata and Artifact Store, all steps preceding the TrainerStep in the pipeline will be cached and re-used in Pipeline B. For large datasets, this will yield enormous benefits in terms of cost and time.

