# zenml.integrations.tensorboard package

## Subpackages

* [zenml.integrations.tensorboard.services package](zenml.integrations.tensorboard.services.md)
  * [Submodules](zenml.integrations.tensorboard.services.md#submodules)
  * [zenml.integrations.tensorboard.services.tensorboard_service module](zenml.integrations.tensorboard.services.md#zenml-integrations-tensorboard-services-tensorboard-service-module)
  * [Module contents](zenml.integrations.tensorboard.services.md#module-contents)
* [zenml.integrations.tensorboard.visualizers package](zenml.integrations.tensorboard.visualizers.md)
  * [Submodules](zenml.integrations.tensorboard.visualizers.md#submodules)
  * [zenml.integrations.tensorboard.visualizers.tensorboard_visualizer module](zenml.integrations.tensorboard.visualizers.md#zenml-integrations-tensorboard-visualizers-tensorboard-visualizer-module)
  * [Module contents](zenml.integrations.tensorboard.visualizers.md#module-contents)

## Module contents

Initialization for TensorBoard integration.

### *class* zenml.integrations.tensorboard.TensorBoardIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of TensorBoard integration for ZenML.

#### NAME *= 'tensorboard'*

#### REQUIREMENTS *: List[str]* *= []*

#### *classmethod* activate() → None

Activates the integration.

#### *classmethod* get_requirements(target_os: str | None = None) → List[str]

Defines platform specific requirements for the integration.

Args:
: target_os: The target operating system.

Returns:
: A list of requirements.
