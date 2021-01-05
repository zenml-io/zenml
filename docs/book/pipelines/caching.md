---
id: caching
title: Caching
description: Get 80% faster with caching!
---

# Caching

Caching is an important mechanism for ZenML. Whenever, you [execute a pipeline](zenml-pipeline-config.md) in the same workspace, the ZenML tracks all the `source` and `args` of your [`Steps`](../steps/creating-custom-steps.md). The outputs of these steps are stored as they are computed. Whenever another pipeline is run afterwards that has a similar configuration to a previously run pipeline, the Core Engine simply uses the previously computed output to **warm start** the pipeline, rather then recomputing the output.

This not only makes each subsequent run potentially much faster but also saves on computing cost.

{% hint style="info" %}
Caching only works across pipelines in the same [artifact store](../repository/artifact-store.md) and same [metadata store](../repository/metadata-store.md). Please make sure to put all related pipelines in the same artifact and metadata store to leverage the advantages of caching.
{% endhint %}

## Credit where credit is due

Our caching is powered by the wonderful [ML Metadata store from the Tensorflow Extended project](https://www.tensorflow.org/tfx/guide/mlmd). TFX is an awesome open-source and free tool by Google, and we use it intensively under-the-hood!

