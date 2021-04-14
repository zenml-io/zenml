---
description: Separate environment from code.
---

# Backends

ZenML backends define `how` and `where` ZenML pipelines are run. They are broadly split into three categories:

* [orchestrator](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/orchestrator-backends.html): Orchestrator backends manage the running of each step of the pipeline
* [processing](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/processing-backends.html): Processing backends defines the environment in which each step executes its workload
* [training](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/training-backends.html): Training backends are special and meant only for [Training Pipelines.](https://github.com/maiot-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/backends/pipelines/training-pipeline.md) They define the environment in which the training happens

By separating backends from the actual pipeline logic, ZenML achieves a [Terraform](https://www.terraform.io/)-like scalability, [extensibility](https://github.com/maiot-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/backends/benefits/integrations.md) and reproducibility for all its pipelines. This is achieved whilst also maintaining comparability and consistent evaluation for all pipelines.

Backends too are split into `standard` and `custom` categories. The standard ones can be found at: `zenml.core.backends.*` .

### How to use a backend?

A backend is associated directly with a [pipeline](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/pipelines/what-is-a-pipeline.html) and can be specified in different ways using the `backends` argument:

* When constructing a pipeline.
* When executing a `pipeline.run()`.
* When executing a `pipeline.build()`.

The API to create custom backends is still under active development. Please see this space for updates.

### What next?[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/what-is-a-backend.html#what-next)

* Set up different [orchestration](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/orchestrator-backends.html) strategies for your pipelines. Execute pipelines on your local

  machine, to a large instance on the cloud, to a Kubernetes cluster.

* Leverage powerful distributed processing by using built-in [processing](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/processing-backends.html) backends.
* Train on GPUs in the cloud with various [training](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/training-backends.html).

## Orchestrator Backends

The orchestrator backend is especially important, as it defines **where** the actual pipeline job runs. Think of it as the `root` of any pipeline job, that controls how and where each individual step within a pipeline is executed. Therefore, the combination of orchestrator and other backends can be used to great effect to scale jobs in production.

The _**orchestrator**_ environment can be the same environment as the _**processing**_ environment, but not neccessarily. E.g. by default a `pipeline.run()` call would result in a local orchestrator and processing backend configuration, meaning the orchestration would be local along with the actual steps. However, if lets say, a dataflow processing backend is chosen, then chosen steps would be executed not in the local enviornment, but on the cloud in Google Dataflow.

### Standard Orchestrators

Please refer to the docstrings within the source code for precise details.

#### Local orchestrator

This is the default orchestrator for ZenML pipelines. It runs pipelines sequentially as a Python process in it’s local environment. You can use this orchestrator for quick experimentation and work on smaller datasets in your local environment.

#### GCP Orchestrator

The GCPOrchestrator can be found at [`OrchestratorGCPBackend`](https://docs.zenml.io/reference/core/backends/orchestrator/gcp/index.html). It spins up a VM on your GCP projects, zips up your local code to the instance, and executes the ZenML pipeline with a Docker Image of your choice.

Best of all, the Orchestrator is capable of launching [preemtible VMs](https://cloud.google.com/compute/docs/instances/preemptible), saving a big chunk of cost along the way.

#### Kubernetes

The KubernetesOrchestrator can be found at [`OrchestratorGCPBackend`](https://docs.zenml.io/reference/core/backends/orchestrator/kubernetes/index.html). It launches a Job on your Kubernetes cluster, zips up your local code to the Pod, and executes the ZenML pipeline with a Docker Image of your choice.

**NOTE:** This Orchestrator requires you to ensure a successful connection between your Kubernetes Cluster and your Metadata Store.

A more extensive guide on creating pipelines with Kubernetes can be found in the [Kubernetes Tutorial](https://github.com/maiot-io/zenml/tree/fc868ee5e5589ef0c09e30be9c2eab4897bfb140/tutorials/running-a-pipeline-on-kubernetes.md).

#### AWS Orchestrator[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/orchestrator-backends.html#aws-orchestrator)

Stay tuned - we’re almost there.

#### Azure Orchestrator[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/orchestrator-backends.html#azure-orchestrator)

Stay tuned - we’re almost there.

#### Kubeflow[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/orchestrator-backends.html#kubeflow)

Coming soon!

### Creating a custom orchestrator[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/orchestrator-backends.html#creating-a-custom-orchestrator)

The API to create custom orchestrators is still under active development. Please see this space for updates.

If you would like to see this functionality earlier, please let us know via our [Slack Channel](https://zenml.io/slack-invite/) or [create an issue on GitHub](https://https//github.com/maiot-io/zenml).

## Processing Backends[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/processing-backends.html#processing-backends)

Some pipelines just need more - processing power, parallelism, permissions, you name it.

A common scenario on large datasets is distributed processing, e.g. via Apache Beam, Google Dataflow, Apache Spark, or other frameworks. In line with our integration-driven design philosophy, ZenML makes it easy to to distribute certain `Steps` in a pipeline \(e.g. in cases where large datasets are involved\). All `Steps` within a pipeline take as input a `ProcessingBackend`.

### Overview[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/processing-backends.html#overview)

The pattern to add a backend to a step is always the same:

```text
backend = ...  # define the backend you want to use
pipeline.add_step(
    Step(...).with_backend(backend)
)
```

![Copy to clipboard](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/_static/copy-button.svg)

### Supported Processing Backends[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/processing-backends.html#supported-processing-backends)

ZenML is built on Apache Beam. You can simple use the `ProcessingBaseBackend`, or extend ZenML with your own, custom backend.+

For convenience, ZenML supports a steadily growing number of processing backends out of the box:

#### Google Dataflow[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/processing-backends.html#google-dataflow)

ZenML natively supports [Google Cloud Dataflow](https://cloud.google.com/dataflow) out of the box \(as it’s built on Apache Beam\).

**Prequisites:**

* [Enable billing](https://cloud.google.com/billing/docs/how-to/modify-project#enable_billing_for_a_project) in your Google Cloud Platform project.
* [Make sure you have permissions](https://cloud.google.com/dataflow/docs/concepts/access-control) to launch dataflow jobs, whether through service account or default credentials.

**Usage:**

```python
# Define the processing backend
processing_backend = ProcessingDataFlowBackend(
    project=GCP_PROJECT,
    staging_location=os.path.join(GCP_BUCKET, 'dataflow_processing/staging'),
)

# Reference the processing backend in steps
# Add a split
training_pipeline.add_split(
    RandomSplit(...).with_backend(
        processing_backend)
)

# Add a preprocessing unit
training_pipeline.add_preprocesser(
    StandardPreprocesser(...).with_backend(processing_backend)
)
```

## Training Backends[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/training-backends.html#training-backends)

ZenML has built-in support for dedicated training backends. These are backends specifically built to provide an edge for training models, e.g. through the availability of GPUs/TPUs, or other performance optimizations.

To use them, simply define your `TrainerStep` along with a `TrainingBackend` for different use-cases.

### Supported Training Backends[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/training-backends.html#supported-training-backends)

#### Google Cloud AI platform[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/training-backends.html#google-cloud-ai-platform)

Google offers a dedicated service for training models with access to GPUs and TPUs called [Google Cloud AI Platform](https://cloud.google.com/ai-platform/docs). ZenML has built-in support to run `TrainingSteps` on Google Cloud AI Platform.

**Prerequisites:**

* [Enable billing](https://cloud.google.com/billing/docs/how-to/modify-project#enable_billing_for_a_project) in your Google Cloud Platform project.
* Make sure you have permissions to launch a training Job on Google AI Platform.
* Make sure you enable the following APIs:
  * Google Cloud AI Platform
  * Cloud SQL
  * Cloud Storage

**Usage:**

```python
from zenml.backends.training import SingleGPUTrainingGCAIPBackend
from zenml.steps.trainer import TFFeedForwardTrainer

(...)

# Add a trainer with a GCAIP backend
training_backend = SingleGPUTrainingGCAIPBackend(
  project=GCP_PROJECT,
  job_dir=TRAINING_JOB_DIR
)

training_pipeline.add_trainer(
  TFFeedForwardTrainer(...).with_backend(training_backend))
```

#### AWS Sagemaker[¶](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/training-backends.html#aws-sagemaker)

Support for AWS Sagemaker is coming soon. Stay tuned to our releases, or let us know on [Slack](https://zenml.io/slack-invite/) if you have an urgent use-case for AWS Sagemaker!

If you would like to see any of this functionality earlier, or if you’re missing a specific backend, please let us know via our [Slack Channel](https://zenml.io/slack-invite/) or [create an issue on GitHub](https://https//github.com/maiot-io/zenml).

