# zenml.integrations.tekton package

## Subpackages

* [zenml.integrations.tekton.flavors package](zenml.integrations.tekton.flavors.md)
  * [Submodules](zenml.integrations.tekton.flavors.md#submodules)
  * [zenml.integrations.tekton.flavors.tekton_orchestrator_flavor module](zenml.integrations.tekton.flavors.md#zenml-integrations-tekton-flavors-tekton-orchestrator-flavor-module)
  * [Module contents](zenml.integrations.tekton.flavors.md#module-contents)
* [zenml.integrations.tekton.orchestrators package](zenml.integrations.tekton.orchestrators.md)
  * [Submodules](zenml.integrations.tekton.orchestrators.md#submodules)
  * [zenml.integrations.tekton.orchestrators.tekton_orchestrator module](zenml.integrations.tekton.orchestrators.md#zenml-integrations-tekton-orchestrators-tekton-orchestrator-module)
  * [Module contents](zenml.integrations.tekton.orchestrators.md#module-contents)

## Module contents

Initialization of the Tekton integration for ZenML.

The Tekton integration sub-module powers an alternative to the local
orchestrator. You can enable it by registering the Tekton orchestrator with
the CLI tool.

### *class* zenml.integrations.tekton.TektonIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Tekton Integration for ZenML.

#### NAME *= 'tekton'*

#### REQUIREMENTS *: List[str]* *= ['kfp>=2.6.0', 'kfp-kubernetes>=1.1.0']*

#### REQUIREMENTS_IGNORED_ON_UNINSTALL *: List[str]* *= ['kfp']*

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the Tekton integration.

Returns:
: List of stack component flavors for this integration.
