# zenml.integrations.neural_prophet package

## Subpackages

* [zenml.integrations.neural_prophet.materializers package](zenml.integrations.neural_prophet.materializers.md)
  * [Submodules](zenml.integrations.neural_prophet.materializers.md#submodules)
  * [zenml.integrations.neural_prophet.materializers.neural_prophet_materializer module](zenml.integrations.neural_prophet.materializers.md#zenml-integrations-neural-prophet-materializers-neural-prophet-materializer-module)
  * [Module contents](zenml.integrations.neural_prophet.materializers.md#module-contents)

## Module contents

Initialization of the Neural Prophet integration.

### *class* zenml.integrations.neural_prophet.NeuralProphetIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of NeuralProphet integration for ZenML.

#### NAME *= 'neural_prophet'*

#### REQUIREMENTS *: List[str]* *= ['neuralprophet>=0.3.2,<0.5.0', 'holidays>=0.4.1,<0.25.0', 'tenacity!=8.4.0']*

#### REQUIREMENTS_IGNORED_ON_UNINSTALL *: List[str]* *= ['tenacity']*

#### *classmethod* activate() → None

Activates the integration.
