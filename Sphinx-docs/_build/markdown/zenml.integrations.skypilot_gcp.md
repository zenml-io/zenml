# zenml.integrations.skypilot_gcp package

## Subpackages

* [zenml.integrations.skypilot_gcp.flavors package](zenml.integrations.skypilot_gcp.flavors.md)
  * [Submodules](zenml.integrations.skypilot_gcp.flavors.md#submodules)
  * [zenml.integrations.skypilot_gcp.flavors.skypilot_orchestrator_gcp_vm_flavor module](zenml.integrations.skypilot_gcp.flavors.md#zenml-integrations-skypilot-gcp-flavors-skypilot-orchestrator-gcp-vm-flavor-module)
  * [Module contents](zenml.integrations.skypilot_gcp.flavors.md#module-contents)
* [zenml.integrations.skypilot_gcp.orchestrators package](zenml.integrations.skypilot_gcp.orchestrators.md)
  * [Submodules](zenml.integrations.skypilot_gcp.orchestrators.md#submodules)
  * [zenml.integrations.skypilot_gcp.orchestrators.skypilot_gcp_vm_orchestrator module](zenml.integrations.skypilot_gcp.orchestrators.md#zenml-integrations-skypilot-gcp-orchestrators-skypilot-gcp-vm-orchestrator-module)
  * [Module contents](zenml.integrations.skypilot_gcp.orchestrators.md#module-contents)

## Module contents

Initialization of the Skypilot GCP integration for ZenML.

The Skypilot integration sub-module powers an alternative to the local
orchestrator for a remote orchestration of ZenML pipelines on VMs.

### *class* zenml.integrations.skypilot_gcp.SkypilotGCPIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Skypilot (GCP) Integration for ZenML.

#### APT_PACKAGES *: List[str]* *= ['openssh-client', 'rsync']*

#### NAME *= 'skypilot_gcp'*

#### REQUIREMENTS *: List[str]* *= ['skypilot[gcp]~=0.6.0']*

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the Skypilot GCP integration.

Returns:
: List of stack component flavors for this integration.
