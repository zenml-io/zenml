# zenml.integrations.prodigy package

## Subpackages

* [zenml.integrations.prodigy.annotators package](zenml.integrations.prodigy.annotators.md)
  * [Submodules](zenml.integrations.prodigy.annotators.md#submodules)
  * [zenml.integrations.prodigy.annotators.prodigy_annotator module](zenml.integrations.prodigy.annotators.md#zenml-integrations-prodigy-annotators-prodigy-annotator-module)
  * [Module contents](zenml.integrations.prodigy.annotators.md#module-contents)
* [zenml.integrations.prodigy.flavors package](zenml.integrations.prodigy.flavors.md)
  * [Submodules](zenml.integrations.prodigy.flavors.md#submodules)
  * [zenml.integrations.prodigy.flavors.prodigy_annotator_flavor module](zenml.integrations.prodigy.flavors.md#zenml-integrations-prodigy-flavors-prodigy-annotator-flavor-module)
  * [Module contents](zenml.integrations.prodigy.flavors.md#module-contents)

## Module contents

Initialization of the Prodigy integration.

### *class* zenml.integrations.prodigy.ProdigyIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Prodigy integration for ZenML.

#### NAME *= 'prodigy'*

#### REQUIREMENTS *: List[str]* *= ['prodigy', 'urllib3<2']*

#### REQUIREMENTS_IGNORED_ON_UNINSTALL *: List[str]* *= ['urllib3']*

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the Prodigy integration.

Returns:
: List of stack component flavors for this integration.
