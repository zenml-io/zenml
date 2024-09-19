# zenml.integrations.feast package

## Subpackages

* [zenml.integrations.feast.feature_stores package](zenml.integrations.feast.feature_stores.md)
  * [Submodules](zenml.integrations.feast.feature_stores.md#submodules)
  * [zenml.integrations.feast.feature_stores.feast_feature_store module](zenml.integrations.feast.feature_stores.md#zenml-integrations-feast-feature-stores-feast-feature-store-module)
  * [Module contents](zenml.integrations.feast.feature_stores.md#module-contents)
* [zenml.integrations.feast.flavors package](zenml.integrations.feast.flavors.md)
  * [Submodules](zenml.integrations.feast.flavors.md#submodules)
  * [zenml.integrations.feast.flavors.feast_feature_store_flavor module](zenml.integrations.feast.flavors.md#zenml-integrations-feast-flavors-feast-feature-store-flavor-module)
  * [Module contents](zenml.integrations.feast.flavors.md#module-contents)

## Module contents

Initialization for Feast integration.

The Feast integration offers a way to connect to a Feast Feature Store. ZenML
implements a dedicated stack component that you can access as part of your ZenML
steps in the usual ways.

### *class* zenml.integrations.feast.FeastIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Feast integration for ZenML.

#### NAME *= 'feast'*

#### REQUIREMENTS *: List[str]* *= ['feast', 'click>=8.0.1,<8.1.4']*

#### REQUIREMENTS_IGNORED_ON_UNINSTALL *: List[str]* *= ['click', 'pandas']*

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the Feast integration.

Returns:
: List of stack component flavors for this integration.

#### *classmethod* get_requirements(target_os: str | None = None) → List[str]

Method to get the requirements for the integration.

Args:
: target_os: The target operating system to get the requirements for.

Returns:
: A list of requirements.
