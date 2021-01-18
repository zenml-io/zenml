# Orchestrator Backends
The orchestrator backend is especially important, as it defines **where** the actual 
pipeline job runs. Think of it as the `root` of any pipeline job, that controls how and where each individual step within 
a pipeline is executed. Therefore, the combination of orchestrator and other backends can be used to great effect to scale 
jobs in production.

The **_orchestrator_** environment can be the same environment as the **_processing_** environment, but not neccessarily. 
E.g. by default a `pipeline.run()` call would result in a local orchestrator and processing backend configuration, 
meaning the orchestration would be local along with the actual steps. However, if lets say, a dataflow processing backend 
is chosen, then chosen steps would be executed not in the local enviornment, but on the cloud in Google Dataflow.

## Standard Orchestrators
Please refer to the docstrings within the source code for precise details the following s

### Local orchestrator
The local orchestrator is used by default. It runs the pipelines sequentially as a Python process on your local machine. 
This is meant for smaller datasets and for quick experimentation.

### GCP Orchestrator

The GCPOrchestrator can be found at `OrchestratorGCPBackend`. 
It spins up a VM on your GCP projects, zips up your code to the instance, and executes the ZenML pipeline with a 
Docker Image of your choice.

Best of all, the Orchestrator

### AWS Orchestrator
Coming Soon!

### Azure Orchestrator
Coming Soon!

### Kubeflow
Coming soon!

### Vanilla Kubernetes
Coming soon!


## Creating a custom orchestrator
The API to create custom orchestrators is still under active development. Please see this space for updates.

If you would like to see this functionality earlier, please let us know via our [Slack Channel](https://zenml.io/slack-invite/) 
or [create an issue on GitHub](https://https://github.com/maiot-io/zenml).
