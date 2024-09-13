# zenml.integrations.xgboost package

## Subpackages

* [zenml.integrations.xgboost.materializers package](zenml.integrations.xgboost.materializers.md)
  * [Submodules](zenml.integrations.xgboost.materializers.md#submodules)
  * [zenml.integrations.xgboost.materializers.xgboost_booster_materializer module](zenml.integrations.xgboost.materializers.md#zenml-integrations-xgboost-materializers-xgboost-booster-materializer-module)
  * [zenml.integrations.xgboost.materializers.xgboost_dmatrix_materializer module](zenml.integrations.xgboost.materializers.md#zenml-integrations-xgboost-materializers-xgboost-dmatrix-materializer-module)
  * [Module contents](zenml.integrations.xgboost.materializers.md#module-contents)

## Module contents

Initialization of the XGBoost integration.

### *class* zenml.integrations.xgboost.XgboostIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of xgboost integration for ZenML.

#### NAME *= 'xgboost'*

#### REQUIREMENTS *: List[str]* *= ['xgboost>=1.0.0']*

#### *classmethod* activate() → None

Activates the integration.
