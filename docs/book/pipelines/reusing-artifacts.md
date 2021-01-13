# Caching

Caching is an important mechanism for ZenML, which not only speeds up ML development, but also allows for re-usability of intermin ML 
artifacts inevitably produced in the experimentation stage of training a ML model.

## Caching gives tremedous benefits
Whenever, [a pipeline](what-is-a-pipeline.md) is run in the same repository, 
ZenML tracks all [Steps](../steps/what-is-a-step.md) executed in the repository. The outputs of these steps are 
stored as they are computed in the [Metadata](../repository/metadata-store.md) and [Artifact](../repository/artifact-store.md) Stores. 
Whenever another pipeline is run afterwards that has the same Step configurations of a previously 
run pipeline, ZenML simply uses the previously computed output to **warm start** the pipeline, rather then recomputing the output.

This not only makes each subsequent run potentially much faster but also saves on computing cost. With ZenML, it is possible to 
[preprocess millions of datapoints](../tutorials/building-a-classifier-on-33m-samples.md). Imagine having to re-compute this each time 
an experiment is run, even if it is a small change to a hyper-parameter of the TrainerStep.

This is usually solved by creating snapshots of preprocessed data unfortuantely stored in random arbitary places. 
In the worst case in local folders, and in the best case in some form of Cloud Storage but with a manually defined order. These 
have the following disadvantages:

* Data might get lost or corrupted
* Data might not be easy to share across teams or environments
* Data can be manipulated unexpectedly and transparently without anyone knowing.

With 

## Example


```warning
Caching only works across pipelines in the same [artifact store](../repository/artifact-store.md) and same [metadata store](../repository/metadata-store.md). Please make sure to put all related pipelines in the same artifact and metadata store to leverage the advantages of caching.
```

## Credit where credit is due

Caching is powered by the wonderful [ML Metadata store from the Tensorflow Extended project](https://www.tensorflow.org/tfx/guide/mlmd). TFX is an awesome open-source and free tool by Google, and we use it intensively under-the-hood!

