# Reusing Artifacts with Caching

Caching is an important mechanism for ZenML, which not only speeds up ML development, but also allows for re-usability of interim ML 
artifacts inevitably produced in the experimentation stage of training an ML model.

## The tremendous benefits of reusing artifacts
Whenever, a [pipeline](../pipelines/what-is-a-pipeline.md) is run in the same repository, 
ZenML tracks all [Steps](../steps/what-is-a-step.md) executed in the repository. The outputs of these steps are 
stored as they are computed in the [Metadata](../repository/metadata-store.md) and [Artifact](../repository/artifact-store.md) Stores. 
Whenever another pipeline is run afterwards that has the same Step configurations of a previously 
run pipeline, ZenML simply uses the previously computed output to **warm start** the pipeline, rather than recomputing the output.

This not only makes each subsequent run potentially much faster but also saves on computing cost. With ZenML, it is possible to 
[preprocess millions of datapoints](../tutorials/building-a-classifier-on-33m-samples.md). Imagine having to re-compute this each time 
an experiment is run, even if it is a small change to a hyper-parameter of the TrainerStep.

This is usually solved by creating snapshots of preprocessed data unfortunately stored in random arbitrary places. 
In the worst case in local folders, and in the best case in some form of Cloud Storage but with a manually defined order. These 
have the following disadvantages:

* Data might get lost or corrupted
* Data might not be easy to share across teams or environments
* Data can be manipulated unexpectedly and transparently without anyone knowing.

With ZenML, all of this is taken care of in the background. Immutable snapshots of interim artifacts are stored in the [Artifact Store](../repository/artifact-store.md) 
and stored for quick reference in the [Metadata Store](../repository/metadata-store.md). Therefore, as long as these remain intact, data cannot be lost, corrupted or 
manipulated in any way unexpectedly. Also, setting up a [collaborative environment with ZenML](../repository/team-collaboration-with-zenml.md) ensures that this data is 
accessible to everyone and is consumed natively by all ZenML steps with ease.

```{warning}
Caching only works across pipelines in the same [artifact store](../repository/artifact-store.md) and same [metadata store](../repository/metadata-store.md). Please make sure to put all related pipelines in the same artifact and metadata store to leverage the advantages of caching.
```

## Example

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

In the above example, if there is a shared Metadata and Artifact Store, all steps preceding the TrainerStep in the pipeline will be cached and re-used in Pipeline B.
For large datasets, this will yield enormous benefits in terms of cost and time.

## Credit where credit is due

Caching is powered by the wonderful [ML Metadata store from the Tensorflow Extended project](https://www.tensorflow.org/tfx/guide/mlmd). TFX is an awesome open-source and free tool by Google, and we use it intensively under-the-hood!

