# Architectural Overview

Getting started with ZenML is easy. It however sports a few nifty details that can transform your pipelines from local experimentation to scaling, distributed pipelines in the cloud quickly.

Conceptually, every ZenML repository has three main aspects to it:

1. Artifact stores
2. Metadata stores
3. Integrations for Orchestration, Processing, Training, and Serving

![High Level Conceptual Diagram of a training pipeline in a ZenML repository](../.gitbook/assets/architecture-overview-zenml.png)

Artifact and metadata stores can be configured per repository as well as per pipeline. However, only pipelines with the same Artifact and Metadata store are comparable, and therefore should not change to maintain the benefits of caching and consistency across pipeline runs.

On a high level, when data is read from a datasource the results are persisted in your artifact store. An orchestration integration reads the data from the artifact store and begins preprocessing - either itself, or alternatively on a dedicated processing backend like [Google Dataflow](https://cloud.google.com/dataflow). Every pipeline step reads it's predecessors result artifacts from the artifact store and writes it's own result artifacts to the artifact store. Once preprocessing is done, the orchestration begins the training of your model - again either itself or on a dedicated training backend. The trained model will be persisted in the artifact store, and optionally passed on to a serving backend.

A few rules apply:

* Every orchestration backend \(local, [Google Cloud VMs](../tutorials/running-a-pipeline-on-a-google-cloud-vm.md), etc\) can run all pipeline steps, including training, of pipelines. 
* Orchestration backends have a selection of compatible processing backends.
* Pipelines can be configured to utilize more powerful processing \(e.g. distributed\) and training \(e.g. Google AI Platform\) backends. 

A quick example for large data sets makes this clearer. By default, your experiments will run locally. Pipelines on large datasets would be severely bottlenecked, so you can configure Google Dataflow as a processing backend for distributed computation, and Google AI Platform as a training backend.

Serving backends play a special role in ZenML, as some are by design tied to public clouds \(e.g. Google AI Platform serving\), while others can be configured independently \(e.g. Seldon\). Please see each serving backend's documentation for more details.

## System design

Our design choices follow the understanding that production-ready model training pipelines need to be immutable, repeatable, discoverable, descriptive, and efficient. ZenML takes care of the orchestration of your pipelines, from sourcing data all the way to continuous training - no matter if you're running somewhere locally, in an on-premise data center, or in the Cloud.

In different words, we're running your preprocessing and model code while taking care of the "Operations" for you: 

* interfacing between the individual processing steps \(splitting, transform, training\), 
* tracking of intermediate results and metadata, 
* caching your processing artifacts,
* parallelization of computing tasks,
* ensuring immutability of your pipelines from data sourcing to model artifacts,
* no matter where - Cloud, On-Premise, or locally.

Since production scenarios often look complex we've built ZenML with integrations in mind. We support an ever-growing range of integrations for processing, training, and serving, and you can always add custom backends via our extensible interfaces.



