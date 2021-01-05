# Orchestrator Backends

Currently there are two orchestrators supported: `local` and `gcp`.

The local one is the one used by default, which runs the pipelines in your local machine.

## GCP Orchestrator

The GCPOrchestrator can be found at `zenml.core.backends.orchestrator.gcp.orchestrator_gcp_backend.OrchestratorGCPBackend`. It spins up a VM on your GCP projects, zips up your code to the instance, and executes the ZenML pipeline with a Docker Image of your choice. More details coming soon.

