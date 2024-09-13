# zenml.integrations.skypilot_azure package

## Subpackages

* [zenml.integrations.skypilot_azure.flavors package](zenml.integrations.skypilot_azure.flavors.md)
  * [Submodules](zenml.integrations.skypilot_azure.flavors.md#submodules)
  * [zenml.integrations.skypilot_azure.flavors.skypilot_orchestrator_azure_vm_flavor module](zenml.integrations.skypilot_azure.flavors.md#zenml-integrations-skypilot-azure-flavors-skypilot-orchestrator-azure-vm-flavor-module)
  * [Module contents](zenml.integrations.skypilot_azure.flavors.md#module-contents)
* [zenml.integrations.skypilot_azure.orchestrators package](zenml.integrations.skypilot_azure.orchestrators.md)
  * [Submodules](zenml.integrations.skypilot_azure.orchestrators.md#submodules)
  * [zenml.integrations.skypilot_azure.orchestrators.skypilot_azure_vm_orchestrator module](zenml.integrations.skypilot_azure.orchestrators.md#zenml-integrations-skypilot-azure-orchestrators-skypilot-azure-vm-orchestrator-module)
  * [Module contents](zenml.integrations.skypilot_azure.orchestrators.md#module-contents)

## Module contents

Initialization of the Skypilot Azure integration for ZenML.

The Skypilot integration sub-module powers an alternative to the local
orchestrator for a remote orchestration of ZenML pipelines on VMs.

### *class* zenml.integrations.skypilot_azure.SkypilotAzureIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Skypilot (Azure) Integration for ZenML.

#### APT_PACKAGES *: List[str]* *= ['openssh-client', 'rsync']*

#### NAME *= 'skypilot_azure'*

#### REQUIREMENTS *: List[str]* *= ['skypilot[azure]>=0.6.1']*

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the Skypilot Azure integration.

Returns:
: List of stack component flavors for this integration.
