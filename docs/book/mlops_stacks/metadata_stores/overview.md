---
description: Tracking the pipeline runs in the metadata store
---

Keeping a historical record of your pipeline runs is a core MLOps practice.
This makes it possible to trace back the lineage or provenance of the data that
was used to train a model, for example, or to go back and compare the
performance of a particular model at different points in time. Features like
these are becoming increasingly important in production ML to help you make
informed decision about the project and to provide better visibility when
something goes wrong. They are especially useful in cases where legal compliance
and liability are a factor.

The Metadata Store is a central component in the MLOps stack where the pipeline
runtime information is versioned and stored. The configuration of each pipeline,
step and produced artifacts are all tracked within the Metadata Store. 

ZenML puts a lot of emphasis on guaranteed tracking of inputs across pipeline
steps. Information about every pipeline run is collected and automatically
recorded in the Metadata Store: the pipeline configuration, the pipeline steps
and their configuration, as well as the types of artifacts produced by pipeline
step runs and the location in the Artifact Store where they are kept. This is
coupled with saving the artifact contents themselves in the [Artifact Store](../artifact_stores/overview.md)
to provide extremely useful features such as caching, provenance/lineage
tracking and pipeline reproducibility.

Related concepts:

* the Metadata Store is a type of Stack Component that needs to be registered as
part of your ZenML [Stack](../../developer-guide/stacks_profiles_repositories.md#stacks).
* the Metadata Store stores information about where the artifacts produced by
your pipelines are kept in the [Artifact Store](../artifact_stores/overview.md).
* the [Orchestrators](../orchestrators/overview.md) are the stack components
responsible for collecting the pipeline runtime information and storing it in
the Metadata Store.
* you can access the information recorded about your pipeline runs in the
Metadata Store using [the post-execution workflow API](../../developer-guide/post-execution-workflow.md).

## When to use it

The Metadata Store is a mandatory component in the ZenML stack. It is used
to keep a log of detailed information about every pipeline run and you are
required to configure it in all of your stacks.

### Metadata Store Flavors

Out of the box, ZenML comes with a `sqlite` Metadata Store already part of the
default stack that stores metadata in a SQLite database file on your local
filesystem and a `mysql` Metadata Store flavor that you can connect to a MySQL
compatible database. Additional Metadata Store flavors are provided by
integrations. These flavors are to be used in different contexts, but in
general, we suggest to use the `mysql` flavor for most use cases:

| Metadata Store | Flavor | Integration | Notes             |
|----------------|--------|-------------|--------------------|
| [SQLite](./sqlite.md) | `sqlite` | _built-in_ | This is the default Metadata Store. It stores metadata information in a SQLite file on your local filesystem. Should be used only for running ZenML locally. |
| [MySQL](./mysql.md) | `mysql` | _built-in_ | Connects to a MySQL compatible database service to store metadata information. Suitable and recommended for most production settings. |
| [Kubeflow](./kubeflow.md) | `kubeflow` | `kubeflow` | Kubeflow deployments include an internal metadata store, which ZenML can leverage. This flavor of Metadata Store can only to be used in combination with the [Kubeflow Orchestrator](../orchestrators/kubeflow.md). |
| [Kubernetes](./kubernetes.md) | `kubernetes` | `kubernetes` | Use this Metadata Store flavor to automatically deploy a MySQL database as a Kubernetes workload and use it as a Metadata Store backend. Not recommended for production settings. |
| [Custom Implementation](./custom.md) | _custom_ |  | _custom_ | Extend the Metadata Store abstraction and provide your own implementation. |

If you would like to see the available flavors of Metadata Stores, you can 
use the command:

```shell
zenml metadata-store flavor list
```

## How to use it

The Metadata Store provides low-level metadata storage services for other ZenML
mechanisms. When you develop ZenML pipelines, you don't even have to be
aware of its existence or interact with it directly. ZenML provides higher-level
APIs that can be used as an alternative to record and access information about
pipeline executions:

* information about your pipeline step executions is automatically recorded in
the Metadata Store.
* use [the post-execution workflow API](../../developer-guide/post-execution-workflow.md)
to retrieve information about your pipeline runs from the active Metadata Store
after a pipeline run is complete.
* use ZenML [Visualizers](../../developer-guide/visualizer.md) to retrieve the
information stored in the Metadata Store about the artifacts produced by a
pipeline step and to display those artifacts as notebook widgets or HTML pages.
