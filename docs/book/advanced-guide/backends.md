---
description: Separate environment from code.
---

# Backends

**ZenML backends** define `how` and `where` **ZenML pipelines** are run. They are broadly split into three categories:

* **orchestrator**: Orchestrator backends manage the running of each **step** of the **pipeline**
* **processing**: Processing backends defines the environment in which each **step** executes its workload
* **training**: Training backends are special and meant only for `TrainingPipeline`s. They define the environment in which the training happens

By separating backends from the actual pipeline logic, ZenML achieves a [Terraform](https://www.terraform.io/)-like scalability, **extensibility** and **reproducibility** for all its pipelines. This is achieved whilst also maintaining comparability and consistent evaluation for all pipelines.

You can then:

* Set up different [orchestration](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/orchestrator-backends.html) strategies for your pipelines. Execute pipelines on your local machine, to a large instance on the cloud, to a Kubernetes cluster.
* Leverage powerful distributed processing by using built-in [processing](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/processing-backends.html) backends.
* Train on GPUs in the cloud with various [training](http://docs.zenml.io.s3-website.eu-central-1.amazonaws.com/backends/training-backends.html).

## How to use a backend?

A backend is associated directly with a [pipeline](../api-reference/zenml/zenml.pipelines.md) and can be specified in different ways using the `backend` argument. The goal of **ZenML** is to get to a point where a data scientist can simply query the backends available for their **ZenML** repo by doing:

```python
repo.get_backends() # fetches all connected backends
```

The creation or connection of backends will be elaborated on in future **ZenML** releases. For now, these docs represent `pre-made` backends that are by default included in the **ZenML** package.

## Orchestrator Backends

The orchestrator backend is especially important, as it defines **where** the actual pipeline job runs. Think of it as the `root` of any pipeline job, that controls how and where each individual step within a pipeline is executed. Therefore, the combination of orchestrator and other backends can be used to great effect to scale jobs in production.

The _**orchestrator**_ environment can be the same environment as the _**processing**_ environment, but not necessarily. E.g. by default, a `pipeline.run()` call would result in a local orchestrator and processing backend configuration, meaning the orchestration would be local along with the actual steps. However, if let's say, a dataflow processing backend is chosen, then chosen steps would be executed not in the local environment, but on the cloud in Google Dataflow.

### Overview

The pattern to add a backend to a step is always the same:

```text
backend = ...  # define the backend you want to use
pipeline.run(backend=backend)
```

### Example

**ZenML** pipelines can be orchestrated on a native Kubernetes cluster.

**Prequisites:**

* This example assumes you have [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/) installed and ready to use. Additionally, it assumes there is a `.kube/config`

**Usage:**

```python
# Define the orchestrator backend
orchestrator_backend = OrchestratorKubernetesBackend(
    kubernetes_config_path=K8S_CONFIG_PATH,
    image_pull_policy="Always")

# Run the pipeline on a Kubernetes Cluster
training_pipeline.run(
    backend=orchestrator_backend,
    metadata_store=metadata_store,
    artifact_store=artifact_store,
)
```

Full example [here](https://github.com/maiot-io/zenml/tree/main/examples/gcp_kubernetes_orchestrated).

## Processing Backends

Some pipelines just need more - processing power, parallelism, permissions, you name it.

A common scenario on large datasets is distributed processing, e.g. via Apache Beam, Google Dataflow, Apache Spark, or other frameworks. In line with our integration-driven design philosophy, **ZenML** makes it easy to distribute certain `Steps` in a pipeline \(e.g. in cases where large datasets are involved\). All `Steps` within a pipeline take as input a `ProcessingBackend`.

### Overview

The pattern to add a processing backend to a step is always the same:

```python
backend = ...  # define the backend you want to use
pipeline.add_step(
    Step(...).with_backend(backend)
)
```

### Example

**ZenML** uses Apache Beam extensively. You can simple use the `ProcessingBaseBackend`, or extend **ZenML** with your own backend. **ZenML** natively supports [Google Cloud Dataflow](https://cloud.google.com/dataflow) out of the box \(as it’s built on Apache Beam\).

**Prequisites:**

* [Enable billing](https://cloud.google.com/billing/docs/how-to/modify-project#enable_billing_for_a_project) in your Google Cloud Platform project.
* [Make sure you have the required permissions](https://cloud.google.com/dataflow/docs/concepts/access-control) to launch dataflow jobs, whether through a service account or default credentials.

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

Full example [here](https://github.com/maiot-io/zenml/tree/main/examples/gcp_kubernetes_orchestrated).

## Training Backends

**ZenML** has built-in support for dedicated training backends. These are backends specifically built to provide an edge for training models, e.g. through the availability of GPUs/TPUs, or other performance optimizations.

In order to use them, simply define your `TrainerStep` along with a `TrainingBackend` for different use-cases.

### Example

Google offers a dedicated service for training models with access to GPUs and TPUs called [Google Cloud AI Platform](https://cloud.google.com/ai-platform/docs). **ZenML** has built-in support to run `TrainingSteps` on Google Cloud AI Platform.

**Prerequisites:**

* [Enable billing](https://cloud.google.com/billing/docs/how-to/modify-project#enable_billing_for_a_project) in your Google Cloud Platform project.
* Make sure you have the required permissions to launch a training Job on Google AI Platform.
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

Full example [here](https://github.com/maiot-io/zenml/tree/main/examples/gcp_kubernetes_orchestrated).

If you would like to see any of this functionality earlier, or if you’re missing a specific backend, please let us know via our [Slack Channel](https://zenml.io/slack-invite/) or [create an issue on GitHub](https://https//github.com/maiot-io/zenml).

