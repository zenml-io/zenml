# zenml.integrations.sklearn package

## Subpackages

* [zenml.integrations.sklearn.materializers package](zenml.integrations.sklearn.materializers.md)
  * [Submodules](zenml.integrations.sklearn.materializers.md#submodules)
  * [zenml.integrations.sklearn.materializers.sklearn_materializer module](zenml.integrations.sklearn.materializers.md#module-zenml.integrations.sklearn.materializers.sklearn_materializer)
    * [`SklearnMaterializer`](zenml.integrations.sklearn.materializers.md#zenml.integrations.sklearn.materializers.sklearn_materializer.SklearnMaterializer)
      * [`SklearnMaterializer.ASSOCIATED_ARTIFACT_TYPE`](zenml.integrations.sklearn.materializers.md#zenml.integrations.sklearn.materializers.sklearn_materializer.SklearnMaterializer.ASSOCIATED_ARTIFACT_TYPE)
      * [`SklearnMaterializer.ASSOCIATED_TYPES`](zenml.integrations.sklearn.materializers.md#zenml.integrations.sklearn.materializers.sklearn_materializer.SklearnMaterializer.ASSOCIATED_TYPES)
  * [Module contents](zenml.integrations.sklearn.materializers.md#module-zenml.integrations.sklearn.materializers)

## Module contents

Initialization of the sklearn integration.

### *class* zenml.integrations.sklearn.SklearnIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of sklearn integration for ZenML.

#### NAME *= 'sklearn'*

#### REQUIREMENTS *: List[str]* *= ['scikit-learn', 'scikit-image']*

#### *classmethod* activate() → None

Activates the integration.
