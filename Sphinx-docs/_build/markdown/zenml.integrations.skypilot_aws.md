# zenml.integrations.skypilot_aws package

## Subpackages

* [zenml.integrations.skypilot_aws.flavors package](zenml.integrations.skypilot_aws.flavors.md)
  * [Submodules](zenml.integrations.skypilot_aws.flavors.md#submodules)
  * [zenml.integrations.skypilot_aws.flavors.skypilot_orchestrator_aws_vm_flavor module](zenml.integrations.skypilot_aws.flavors.md#zenml-integrations-skypilot-aws-flavors-skypilot-orchestrator-aws-vm-flavor-module)
  * [Module contents](zenml.integrations.skypilot_aws.flavors.md#module-contents)
* [zenml.integrations.skypilot_aws.orchestrators package](zenml.integrations.skypilot_aws.orchestrators.md)
  * [Submodules](zenml.integrations.skypilot_aws.orchestrators.md#submodules)
  * [zenml.integrations.skypilot_aws.orchestrators.skypilot_aws_vm_orchestrator module](zenml.integrations.skypilot_aws.orchestrators.md#zenml-integrations-skypilot-aws-orchestrators-skypilot-aws-vm-orchestrator-module)
  * [Module contents](zenml.integrations.skypilot_aws.orchestrators.md#module-contents)

## Module contents

Initialization of the Skypilot AWS integration for ZenML.

The Skypilot integration sub-module powers an alternative to the local
orchestrator for a remote orchestration of ZenML pipelines on VMs.

### *class* zenml.integrations.skypilot_aws.SkypilotAWSIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Skypilot AWS Integration for ZenML.

#### APT_PACKAGES *: List[str]* *= ['openssh-client', 'rsync']*

#### NAME *= 'skypilot_aws'*

#### REQUIREMENTS *: List[str]* *= ['skypilot[aws]~=0.6.0']*

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the Skypilot AWS integration.

Returns:
: List of stack component flavors for this integration.
