# zenml.integrations.skypilot_lambda package

## Subpackages

* [zenml.integrations.skypilot_lambda.flavors package](zenml.integrations.skypilot_lambda.flavors.md)
  * [Submodules](zenml.integrations.skypilot_lambda.flavors.md#submodules)
  * [zenml.integrations.skypilot_lambda.flavors.skypilot_orchestrator_lambda_vm_flavor module](zenml.integrations.skypilot_lambda.flavors.md#zenml-integrations-skypilot-lambda-flavors-skypilot-orchestrator-lambda-vm-flavor-module)
  * [Module contents](zenml.integrations.skypilot_lambda.flavors.md#module-contents)
* [zenml.integrations.skypilot_lambda.orchestrators package](zenml.integrations.skypilot_lambda.orchestrators.md)
  * [Submodules](zenml.integrations.skypilot_lambda.orchestrators.md#submodules)
  * [zenml.integrations.skypilot_lambda.orchestrators.skypilot_lambda_vm_orchestrator module](zenml.integrations.skypilot_lambda.orchestrators.md#zenml-integrations-skypilot-lambda-orchestrators-skypilot-lambda-vm-orchestrator-module)
  * [Module contents](zenml.integrations.skypilot_lambda.orchestrators.md#module-contents)

## Module contents

Initialization of the Skypilot Lambda integration for ZenML.

The Skypilot integration sub-module powers an alternative to the local
orchestrator for a remote orchestration of ZenML pipelines on VMs.

### *class* zenml.integrations.skypilot_lambda.SkypilotLambdaIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Skypilot Lambda Integration for ZenML.

#### NAME *= 'skypilot_lambda'*

#### REQUIREMENTS *: List[str]* *= ['skypilot[lambda]~=0.6.0']*

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the Skypilot Lambda integration.

Returns:
: List of stack component flavors for this integration.
