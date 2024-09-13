# zenml.integrations.pycaret package

## Subpackages

* [zenml.integrations.pycaret.materializers package](zenml.integrations.pycaret.materializers.md)
  * [Submodules](zenml.integrations.pycaret.materializers.md#submodules)
  * [zenml.integrations.pycaret.materializers.model_materializer module](zenml.integrations.pycaret.materializers.md#zenml-integrations-pycaret-materializers-model-materializer-module)
  * [Module contents](zenml.integrations.pycaret.materializers.md#module-contents)

## Module contents

Initialization of the PyCaret integration.

### *class* zenml.integrations.pycaret.PyCaretIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of PyCaret integration for ZenML.

#### NAME *= 'pycaret'*

#### REQUIREMENTS *: List[str]* *= ['pycaret>=3.0.0', 'scikit-learn', 'xgboost', 'catboost', 'lightgbm']*

#### REQUIREMENTS_IGNORED_ON_UNINSTALL *: List[str]* *= ['scikit-learn', 'xgboost', 'catboost', 'lightgbm']*

#### *classmethod* activate() → None

Activates the integration.
