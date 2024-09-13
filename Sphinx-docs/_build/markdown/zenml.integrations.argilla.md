# zenml.integrations.argilla package

## Subpackages

* [zenml.integrations.argilla.annotators package](zenml.integrations.argilla.annotators.md)
  * [Submodules](zenml.integrations.argilla.annotators.md#submodules)
  * [zenml.integrations.argilla.annotators.argilla_annotator module](zenml.integrations.argilla.annotators.md#zenml-integrations-argilla-annotators-argilla-annotator-module)
  * [Module contents](zenml.integrations.argilla.annotators.md#module-contents)
* [zenml.integrations.argilla.flavors package](zenml.integrations.argilla.flavors.md)
  * [Submodules](zenml.integrations.argilla.flavors.md#submodules)
  * [zenml.integrations.argilla.flavors.argilla_annotator_flavor module](zenml.integrations.argilla.flavors.md#zenml-integrations-argilla-flavors-argilla-annotator-flavor-module)
  * [Module contents](zenml.integrations.argilla.flavors.md#module-contents)

## Module contents

Initialization of the Argilla integration.

### *class* zenml.integrations.argilla.ArgillaIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Argilla integration for ZenML.

#### NAME *= 'argilla'*

#### REQUIREMENTS *: List[str]* *= ['argilla>=1.20.0,<2']*

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the Argilla integration.

Returns:
: List of stack component flavors for this integration.
