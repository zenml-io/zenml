# zenml.integrations.lightning package

## Subpackages

* [zenml.integrations.lightning.flavors package](zenml.integrations.lightning.flavors.md)
  * [Submodules](zenml.integrations.lightning.flavors.md#submodules)
  * [zenml.integrations.lightning.flavors.lightning_orchestrator_flavor module](zenml.integrations.lightning.flavors.md#zenml-integrations-lightning-flavors-lightning-orchestrator-flavor-module)
  * [Module contents](zenml.integrations.lightning.flavors.md#module-contents)
* [zenml.integrations.lightning.orchestrators package](zenml.integrations.lightning.orchestrators.md)
  * [Submodules](zenml.integrations.lightning.orchestrators.md#submodules)
  * [zenml.integrations.lightning.orchestrators.lightning_orchestrator module](zenml.integrations.lightning.orchestrators.md#zenml-integrations-lightning-orchestrators-lightning-orchestrator-module)
  * [zenml.integrations.lightning.orchestrators.lightning_orchestrator_entrypoint module](zenml.integrations.lightning.orchestrators.md#zenml-integrations-lightning-orchestrators-lightning-orchestrator-entrypoint-module)
  * [zenml.integrations.lightning.orchestrators.lightning_orchestrator_entrypoint_configuration module](zenml.integrations.lightning.orchestrators.md#zenml-integrations-lightning-orchestrators-lightning-orchestrator-entrypoint-configuration-module)
  * [zenml.integrations.lightning.orchestrators.utils module](zenml.integrations.lightning.orchestrators.md#zenml-integrations-lightning-orchestrators-utils-module)
  * [Module contents](zenml.integrations.lightning.orchestrators.md#module-contents)

## Module contents

Initialization of the Lightning integration for ZenML.

### *class* zenml.integrations.lightning.LightningIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Lightning Integration for ZenML.

#### NAME *= 'lightning'*

#### REQUIREMENTS *: List[str]* *= ['lightning-sdk']*

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the Lightning integration.

Returns:
: List of stack component flavors for this integration.
