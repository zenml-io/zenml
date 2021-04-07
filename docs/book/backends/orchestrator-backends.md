# Orchestrator Backends

The orchestrator backend is especially important, as it defines **where** the actual pipeline job runs. Think of it as the `root` of any pipeline job, that controls how and where each individual step within a pipeline is executed. Therefore, the combination of orchestrator and other backends can be used to great effect to scale jobs in production.

The _**orchestrator**_ environment can be the same environment as the _**processing**_ environment, but not neccessarily. E.g. by default a `pipeline.run()` call would result in a local orchestrator and processing backend configuration, meaning the orchestration would be local along with the actual steps. However, if lets say, a dataflow processing backend is chosen, then chosen steps would be executed not in the local enviornment, but on the cloud in Google Dataflow.

## Standard Orchestrators

Please refer to the docstrings within the source code for precise details.

### Local orchestrator

This is the default orchestrator for ZenML pipelines. It runs pipelines sequentially as a Python process in it's local environment. You can use this orchestrator for quick experimentation and work on smaller datasets in your local environment.

### GCP Orchestrator

The GCPOrchestrator can be found at [`OrchestratorGCPBackend`](https://docs.zenml.io/reference/core/backends/orchestrator/gcp/index.html). It spins up a VM on your GCP projects, zips up your local code to the instance, and executes the ZenML pipeline with a Docker Image of your choice.

Best of all, the Orchestrator is capable of launching [preemtible VMs](https://cloud.google.com/compute/docs/instances/preemptible), saving a big chunk of cost along the way.

### Kubernetes

The KubernetesOrchestrator can be found at [`OrchestratorGCPBackend`](https://docs.zenml.io/reference/core/backends/orchestrator/kubernetes/index.html). It launches a Job on your Kubernetes cluster, zips up your local code to the Pod, and executes the ZenML pipeline with a Docker Image of your choice.

**NOTE:** This Orchestrator requires you to ensure a successful connection between your Kubernetes Cluster and your Metadata Store.

A more extensive guide on creating pipelines with Kubernetes can be found in the [Kubernetes Tutorial](https://github.com/maiot-io/zenml/tree/fc868ee5e5589ef0c09e30be9c2eab4897bfb140/tutorials/running-a-pipeline-on-kubernetes.md).

### AWS Orchestrator

Stay tuned - we're almost there.

### Azure Orchestrator

Stay tuned - we're almost there.

### Kubeflow

Coming soon!

## Creating a custom orchestrator

The API to create custom orchestrators is still under active development. Please see this space for updates.

If you would like to see this functionality earlier, please let us know via our [Slack Channel](https://zenml.io/slack-invite/) or [create an issue on GitHub](https://https://github.com/maiot-io/zenml).

