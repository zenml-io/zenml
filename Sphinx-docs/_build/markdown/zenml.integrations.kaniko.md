# zenml.integrations.kaniko package

## Subpackages

* [zenml.integrations.kaniko.flavors package](zenml.integrations.kaniko.flavors.md)
  * [Submodules](zenml.integrations.kaniko.flavors.md#submodules)
  * [zenml.integrations.kaniko.flavors.kaniko_image_builder_flavor module](zenml.integrations.kaniko.flavors.md#zenml-integrations-kaniko-flavors-kaniko-image-builder-flavor-module)
  * [Module contents](zenml.integrations.kaniko.flavors.md#module-contents)
* [zenml.integrations.kaniko.image_builders package](zenml.integrations.kaniko.image_builders.md)
  * [Submodules](zenml.integrations.kaniko.image_builders.md#submodules)
  * [zenml.integrations.kaniko.image_builders.kaniko_image_builder module](zenml.integrations.kaniko.image_builders.md#zenml-integrations-kaniko-image-builders-kaniko-image-builder-module)
  * [Module contents](zenml.integrations.kaniko.image_builders.md#module-contents)

## Module contents

Kaniko integration for image building.

### *class* zenml.integrations.kaniko.KanikoIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of the Kaniko integration for ZenML.

#### NAME *= 'kaniko'*

#### REQUIREMENTS *: List[str]* *= []*

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the Kaniko integration.

Returns:
: List of new stack component flavors.
