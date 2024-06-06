---
description: Use Skypilot with ZenML.
---

# Skypilot

The ZenML SkyPilot VM Orchestrator allows you to provision and manage VMs on any supported cloud provider (AWS, GCP, Azure, Lambda Labs) for running your ML pipelines. It simplifies the process and offers cost savings and high GPU availability.

## Prerequisites

To use the SkyPilot VM Orchestrator, you'll need:

- ZenML SkyPilot integration for your cloud provider installed (`zenml integration install <PROVIDER> skypilot_<PROVIDER>`)
- Docker installed and running
- A remote artifact store and container registry in your ZenML stack
- A remote ZenML deployment
- Appropriate permissions to provision VMs on your cloud provider
- A service connector configured to authenticate with your cloud provider (not needed for Lambda Labs)

## Configuring the Orchestrator

Configuration steps vary by cloud provider:

AWS, GCP, Azure:
1. Install the SkyPilot integration and connectors extra for your provider
2. Register a service connector with credentials that have SkyPilot's required permissions 
3. Register the orchestrator and connect it to the service connector
4. Register and activate a stack with the new orchestrator

```bash
zenml service-connector register <PROVIDER>-skypilot-vm -t <PROVIDER> --auto-configure
zenml orchestrator register <ORCHESTRATOR_NAME> --flavor vm_<PROVIDER>  
zenml orchestrator connect <ORCHESTRATOR_NAME> --connector <PROVIDER>-skypilot-vm
zenml stack register <STACK_NAME> -o <ORCHESTRATOR_NAME> ... --set
```

Lambda Labs:
1. Install the SkyPilot Lambda integration 
2. Register a secret with your Lambda Labs API key
3. Register the orchestrator with the API key secret
4. Register and activate a stack with the new orchestrator

```bash
zenml secret create lambda_api_key --scope user --api_key=<KEY>
zenml orchestrator register <ORCHESTRATOR_NAME> --flavor vm_lambda --api_key={{lambda_api_key.api_key}}
zenml stack register <STACK_NAME> -o <ORCHESTRATOR_NAME> ... --set
```

## Running a Pipeline

Once configured, you can run any ZenML pipeline using the SkyPilot VM Orchestrator. Each step will run in a Docker container on a provisioned VM.

## Additional Configuration

You can further configure the orchestrator using cloud-specific `Settings` objects:

```python
from zenml.integrations.skypilot_<PROVIDER>.flavors.skypilot_orchestrator_<PROVIDER>_vm_flavor import Skypilot<PROVIDER>OrchestratorSettings

skypilot_settings = Skypilot<PROVIDER>OrchestratorSettings(
   cpus="2",
   memory="16", 
   accelerators="V100:2",
   use_spot=True,
   region=<REGION>,
   ...  
)

@pipeline(
   settings={
       "orchestrator.vm_<PROVIDER>": skypilot_settings
   }
)
```

This allows specifying VM size, spot usage, region, and more.

You can also configure resources per step:

```
high_resource_settings = Skypilot<PROVIDER>OrchestratorSettings(...)

@step(settings={"orchestrator.vm_<PROVIDER>": high_resource_settings})  
def resource_intensive_step():
   ...
```

For more details and advanced options, see the [full SkyPilot VM Orchestrator documentation](../../component-guide/orchestrators/skypilot-vm.md).

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
