# Extensibility with integrations
The Machine Learning landscape is evolving at a rapid pace. ZenML decouples the experiment workflow from the tooling by providing integrations 
to solutions for specific aspects of your ML pipelines. It is designed with extensibility in mind. 

This means that the goal of ZenML is to be able to work with any 
ML tool in the eco-system seamlessly. There are multiple ways to use ZenML with other libraries.

## Integrations
ZenML uses the `extra_requires` field provided in Python [setuptools](https://setuptools.readthedocs.io/en/latest/setuptools.html) 
which allows for defining plugin-like dependencies for integrations. These integrations can then accessed via pip at installation time 
with the `[]` operators. E.g.

```bash
pip install zenml[pytorch]
```

Will unlock the `pytorch` integration for ZenML, allowing users to use the `PyTorchTrianerStep` for example.

To install all dependencies, use:

```bash
pip install zenml[all]
```

```{warning}
Using the [all] keyword will result in a significantly bigger package installation.
```

In order to see the full list of integrations available, see the [setup.py on GitHub](https://github.com/maiot-io/zenml/blob/main/setup.py).

We would be happy to see [your contributions for more integrations](https://github.com/maiot-io/zenml/) if the ones we have currently support 
not fulfil your requirements. Also let us know via [slack](https://zenml.io/slack-invite) what integrations to add!

## Types of integrations
Integrations can be in the form of `backends` and `steps`. One group of integrations might bring multiple of these. 
E.g. The `gcp` integration brings orchestrator backends, dataflow processing backend and Google Cloud AI Platform training 
backend.

### Orchestration
When you configure an orchestration backend for your pipeline, the environment you execute actual `pipeline.run()` will launch all pipeline steps at the configured orchestration backend, not the local environment. ZenML will attempt to use credentials for the orchestration backend in question from the current environment. **NOTE:** If no further pipeline configuration if provided \(e.g. processing or training backends\), the orchestration backend will also run all pipeline steps.

A quick overview of the currently supported backends:

| **Orchestrator** | **Status** |
| :--- | :--- |
| Google Cloud VMs | &gt;= 0.1.5 |
| Kubernetes | &gt;0.2.0 |
| Kubeflow | WIP |

Integrating custom orchestration backends is fairly straightforward. Check out our example implementation of [Google Cloud VMs](../tutorials/running-a-pipeline-on-a-google-cloud-vm.md) to learn more about building your own integrations.

### (Distributed) Processing

Sometimes, pipeline steps just need more scalability than what your orchestration backend can offer. That’s when the natively distributable codebase of ZenML can shine - it’s straightforward to run pipeline steps on processing backends like Google Dataflow or Apache Spark.

ZenML is using Apache Beam for its pipeline steps, therefore backends rely on the functionality of Apache Beam. A processing backend will execute all pipeline steps before the actual training.

Processing backends can be used to great effect in conjunction with an orchestration backend. To give a practical example: You can orchestrate your pipelines using Google Cloud VMs and configure to use a service account with permissions for Google Dataflow and Google Cloud AI Platform. That way you don’t need to have very open permissions on your personal IAM user, but can relay authority to service-accounts within Google Cloud.

We’re adding support for processing backends continuously:

| **Backend** | **Status** |
| :--- | :--- |
| Google Cloud Dataflow | &gt;= 0.1.5 |
| Apache Spark | WIP |
| AWS EMR | WIP |
| Flink | planned: Q3/2021 |

### Training

Many ML use-cases and model architectures require GPUs/TPUs. ZenML offers integrations to Cloud-based ML training offers and provides a way to extend the training interface to allow for self-built training backends.

Some of these integrations rely on Docker containers or other methods of transmitting code. Please see the documentation for a specific training backend for further details.

| **Backend** | **Status** |
| :--- | :--- |
| Google Cloud AI Platform | &gt;= 0.1.5 |
| PyTorch | &gt;= 0.2.0 |
| AWS Sagemaker | WIP |
| Azure Machine Learning | planned: Q3/2021 |

### Serving

Every ZenML pipeline yields a servable model, ready to be used in your existing architecture - for example as additional input for your CI/CD pipelines. To accommodate other architectures, ZenML has support for a growing number of dedicated serving integrations, with clear linkage and lineage from data to deployment.
These serving integrations come mostly in the form of `DeployerStep`'s to be used inside ZenML pipelines.

| **Backend** | **Status** |
| :--- | :--- |
| Google Cloud AI Platform | &gt;= 0.1.5 |
| Cortex | &gt;0.2.1 |
| AWS Sagemaker | WIP |
| Seldon | planned: Q1/2021 |
| Azure Machine Learning | planned: Q3/2021 |

## Other libraries
If the integrations above do not fulfill your requirements and more dependencies are required, then there is always the option to simply 
install the dependencies alongside ZenML in your repository, and then create [custom steps](../steps/what-is-a-step.md) for your logic. 

If going down this route, one must ensure that the added dependencies do not clash with any [dependency bundled with ZenML](https://github.com/maiot-io/zenml/blob/main/setup.py). 
A good way to check is to [create a custom Docker image](../backends/using-docker.md) with the ZenML base image and then run a simple pipeline to make sure everything works.
