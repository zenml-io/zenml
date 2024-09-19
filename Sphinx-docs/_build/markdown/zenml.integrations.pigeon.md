# zenml.integrations.pigeon package

## Subpackages

* [zenml.integrations.pigeon.annotators package](zenml.integrations.pigeon.annotators.md)
  * [Submodules](zenml.integrations.pigeon.annotators.md#submodules)
  * [zenml.integrations.pigeon.annotators.pigeon_annotator module](zenml.integrations.pigeon.annotators.md#zenml-integrations-pigeon-annotators-pigeon-annotator-module)
  * [Module contents](zenml.integrations.pigeon.annotators.md#module-contents)
* [zenml.integrations.pigeon.flavors package](zenml.integrations.pigeon.flavors.md)
  * [Submodules](zenml.integrations.pigeon.flavors.md#submodules)
  * [zenml.integrations.pigeon.flavors.pigeon_annotator_flavor module](zenml.integrations.pigeon.flavors.md#zenml-integrations-pigeon-flavors-pigeon-annotator-flavor-module)
  * [Module contents](zenml.integrations.pigeon.flavors.md#module-contents)

## Module contents

Initialization of the Pigeon integration.

### *class* zenml.integrations.pigeon.PigeonIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Pigeon integration for ZenML.

#### NAME *= 'pigeon'*

#### REQUIREMENTS *: List[str]* *= ['ipywidgets>=8.0.0']*

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the Pigeon integration.

Returns:
: List of stack component flavors for this integration.
