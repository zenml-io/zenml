# Core Concepts

At its core, ZenML will orchestrate your experiment pipelines from **sourcing data** to **splitting, preprocessing, training**, all the way to the 
**evaluation of results** and even **serving**.

While there are other pipelining solutions for Machine Learning experiments, ZenML is focussed on two unique approaches:

* [Reproducibility](core-concepts.md#reproducibility). 
* [Integrations](core-concepts.md#integrations).

Let us introduce some of the concepts we use to make this focus a reality.

## Reproducibility

ZenML is built with reproducibility in mind. Reproducibility is a core motivation of DevOps methodologies: Builds need to be reproducible. Commonly, this is achieved by version control of code, version pinning of dependencies, and automation of workflows. ZenML bundles these practices into a coherent framework for Machine Learning. Machine Learning brings an added level of complexity to version control, beyond versioning code: Data is inherently hard to version.

### Versioning of data

ZenML takes an easy, yet effective approach to version controlling data. When sourcing data, either via dedicated data pipelines or within your training pipelines, ZenML creates an immutable snapshot of the data \(TFRecords\) used for your specific pipeline. This snapshot is tracked, just like any other pipeline step, and becomes available as a starting point to subsequent pipelines when using the same parameters for sourcing data.

**NOTE:** The principle behind versioning data in ZenML is a variation of the method used for caching pipeline steps.

### Versioning of code

It is not necessary to reinvent the wheel when it comes to version control of code - chances are, you’re already using git to do so \(and if not, you should\). ZenML can tap into a repository's history and allow for version-pinning of your own code via git SHA’s.

This becomes exceptionally powerful when you have code you want/need to embed at serving time, as there is now not just the lineage of data, but also the lineage of code from experiment to serving.

### Declarative configuration

Declarative configurations are a staple of DevOps methodologies, ultimately brought to fame through [Terraform](https://terraform.io/). In a nutshell: A pipeline’s configuration declares the “state” the pipeline should be in and the processing that should be applied, and ZenML figures out where the code lies and what computations to apply.

That way, when your teammate clones your repo and re-runs a pipeline config on a different environment, the pipeline remains reproducible.

### Metadata tracking

While versioning and declarative configs are essential for reproducibility, there needs to be a system that keeps track of all processes as they happen. Google’s [ML Metadata](https://github.com/google/ml-metadata) standardizes metadata tracking and makes it easy to keep track of iterative experimentation as it happens. ZenML uses ML Metadata extensively \(natively as well as via the TFX interface\) to automatically track all **relevant** parameters that are created through ZenML pipeline interfaces. This not only helps in post-training workflows to compare results as experiments progress but also has the added advantage of leveraging caching of pipeline steps.

## Integrations

The Machine Learning landscape is evolving at a rapid pace. We’re decoupling your experiment workflow from the tooling by providing integrations to solutions for specific aspects of your ML pipelines.

### Metadata and Artifacts

With ZenML, inputs and outputs are tracked for every pipeline step. Output artifacts \(e.g. binary representations of data, splits, preprocessing results, models\) are centrally stored and are automatically used for [caching](../benefits/reusing-artifacts.md). To facilitate that, ZenML relies on a Metadata Store and an Artifact Store.

By default, both will point to a subfolder of your local `.zenml` directory, which is created when you run `zenml init`. It’ll contain both the Metadata Store \(default: SQLite\) as well as the Artifact Store \(default: tf.Records in local folders\).

More advanced configurations might want to centralize both the Metadata as well as the Artifact Store, for example for use in Continuous Integration or for collaboration across teams:

The Metadata Store can be simply configured to use any MySQL server \(=&gt;5.6\):

```text
zenml config metadata set mysql \
    --host 127.0.0.1 \ 
    --port 3306 \
    --username USER \
    --passwd PASSWD \
    --database DATABASE
```

The Artifact Store offers native support for Google Cloud Storage:

```text
zenml config artifacts set gs://your-bucket/sub/dir
```

### Orchestration

As ZenML is centered on decoupling workflow from tooling we provide a growing number of out-of-the-box supported backends for orchestration.

When you configure an orchestration backend for your pipeline, the environment you execute actual `pipeline.run()` will launch all pipeline steps at the configured orchestration backend, not the local environment. ZenML will attempt to use credentials for the orchestration backend in question from the current environment. **NOTE:** If no further pipeline configuration if provided \(e.g. processing or training backends\), the orchestration backend will also run all pipeline steps.

A quick overview of the currently supported backends:

| **Orchestrator** | **Status** |
| :--- | :--- |
| Google Cloud VMs | &gt;0.1 |
| Kubernetes | Q1/2021 |
| Kubeflow | WIP |

Integrating custom orchestration backends is fairly straightforward. Check out our example implementation of [Google Cloud VMs](https://github.com/maiot-io/zenml/blob/staging/path/to/pgo.py) to learn more about building your own integrations.

### Distributed Processing



Sometimes, pipeline steps just need more scalability than what your orchestration backend can offer. That’s when the natively distributable codebase of ZenML can shine - it’s straightforward to run pipeline steps on processing backends like Google Dataflow or Apache Spark.

ZenML is using Apache Beam for its pipeline steps, therefore backends rely on the functionality of Apache Beam. A processing backend will execute all pipeline steps before the actual training.

Processing backends can be used to great effect in conjunction with an orchestration backend. To give a practical example: You can orchestrate your pipelines using Google Cloud VMs and configure to use a service account with permissions for Google Dataflow and Google Cloud AI Platform. That way you don’t need to have very open permissions on your personal IAM user, but can relay authority to service-accounts within Google Cloud.

We’re adding support for processing backends continuously:

| **Backend** | **Status** |
| :--- | :--- |
| Google Cloud Dataflow | &gt;0.1 |
| Apache Spark | WIP |
| AWS EMR | WIP |
| Flink | planned: Q3/2021 |

### Training

Many ML use-cases and model architectures require GPUs/TPUs. ZenML offers integrations to Cloud-based ML training offers and provides a way to extend the training interface to allow for self-built training backends.

Some of these backends rely on Docker containers or other methods of transmitting code. Please see the documentation for a specific training backend for further details.

| **Backend** | **Status** |
| :--- | :--- |
| Google Cloud AI Platform | &gt;0.1 |
| AWS Sagemaker | WIP |
| Azure Machine Learning | planned: Q3/2021 |

### Serving

Every ZenML pipeline yields a servable model, ready to be used in your existing architecture - for example as additional input for your CI/CD pipelines. To accommodate other architectures, ZenML has support for a growing number of dedicated serving backends, with clear linkage and lineage from data to deployment.

| **Backend** | **Status** |
| :--- | :--- |
| Google Cloud AI Platform | &gt;0.1 |
| AWS Sagemaker | WIP |
| Seldon | planned: Q1/2021 |
| Azure Machine Learning | planned: Q3/2021 |

