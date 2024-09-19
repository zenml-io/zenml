# zenml.integrations.lightgbm package

## Subpackages

* [zenml.integrations.lightgbm.materializers package](zenml.integrations.lightgbm.materializers.md)
  * [Submodules](zenml.integrations.lightgbm.materializers.md#submodules)
  * [zenml.integrations.lightgbm.materializers.lightgbm_booster_materializer module](zenml.integrations.lightgbm.materializers.md#zenml-integrations-lightgbm-materializers-lightgbm-booster-materializer-module)
  * [zenml.integrations.lightgbm.materializers.lightgbm_dataset_materializer module](zenml.integrations.lightgbm.materializers.md#zenml-integrations-lightgbm-materializers-lightgbm-dataset-materializer-module)
  * [Module contents](zenml.integrations.lightgbm.materializers.md#module-contents)

## Module contents

Initialization of the LightGBM integration.

### *class* zenml.integrations.lightgbm.LightGBMIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of lightgbm integration for ZenML.

#### APT_PACKAGES *: List[str]* *= ['libgomp1']*

#### NAME *= 'lightgbm'*

#### REQUIREMENTS *: List[str]* *= ['lightgbm>=1.0.0']*

#### *classmethod* activate() → None

Activates the integration.
