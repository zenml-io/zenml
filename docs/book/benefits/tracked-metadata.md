# Automatically track ML Metadata

ZenML uses Google’s [ML Metadata](https://github.com/google/ml-metadata) under-the-hood to automatically track all 
metadata produced by ZenML pipelines. ML Metadata standardizes metadata tracking and makes it easy to keep track of iterative experimentation as it 
happens. This not only helps in post-training workflows to [compare results](../pipelines/training-pipeline.md) as experiments progress but also has the added advantage of leveraging 
[caching](../benefits/reusing-artifacts.md) of pipeline steps.

## How does it work?
All parameters of every ZenML step are persisted in the [Metadata Store](../repository/metadata-store.md) and also in the 
[declarative pipeline configs](../pipelines/what-is-a-pipeline.md). In the config, they can be seen quite easily in the `steps` 
key. Here is a sample stemming from this Python step:

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

The `args` key represents all the parameters captured and persisted.

Under-the-hood, these parameters are also captured as [ExecutionParameters](https://www.tensorflow.org/tfx/api_docs/python/tfx/types/component_spec/ExecutionParameter) in 
[TFX components](https://www.tensorflow.org/tfx/api_docs/python/tfx/components), therefore they are directly inserted into the 
`Execution` table of the MLMetadata store. 

For most use-cases, ZenML exposes native interfaces to fetch these parameters after a pipeline has been run successfully. 
E.g. the `repo.compare_training_runs()` method compares all pipelines in a Repository() and extensively uses the ML Metadata store 
to spin up a visualization of comparison of training pipeline results.

However, if users would like direct access to the store, they can easily use the ML Metadata Python library to quickly access their 
parameters. To understand more about how Execution Parameters and ML Metadata work 
please refer to the [TFX docs](https://www.tensorflow.org/tfx/guide/mlmd).

## How to specify what to track
As all steps are persisted in the same pattern show above, it is very simple to track any metadata you desire. 
Whenever creating a [custom step](../steps/what-is-a-step.md), simply add the parameters you want to track as 
**kwargs** (keyworded parameters) in your Step `__init__()` method (i.e. the constructor).

ZenML ensures that all kwargs of all steps are tracked automatically.

```{warning}
As outlined in the Steps definition, for now, only primitive types are supported for tracking. You cannot track any arbitrary 
python object. Please ensure that only primitive types (int, string, float etc) are used in your Step constructors.
```