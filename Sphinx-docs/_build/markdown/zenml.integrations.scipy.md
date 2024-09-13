# zenml.integrations.scipy package

## Subpackages

* [zenml.integrations.scipy.materializers package](zenml.integrations.scipy.materializers.md)
  * [Submodules](zenml.integrations.scipy.materializers.md#submodules)
  * [zenml.integrations.scipy.materializers.sparse_materializer module](zenml.integrations.scipy.materializers.md#module-zenml.integrations.scipy.materializers.sparse_materializer)
    * [`SparseMaterializer`](zenml.integrations.scipy.materializers.md#zenml.integrations.scipy.materializers.sparse_materializer.SparseMaterializer)
      * [`SparseMaterializer.ASSOCIATED_ARTIFACT_TYPE`](zenml.integrations.scipy.materializers.md#zenml.integrations.scipy.materializers.sparse_materializer.SparseMaterializer.ASSOCIATED_ARTIFACT_TYPE)
      * [`SparseMaterializer.ASSOCIATED_TYPES`](zenml.integrations.scipy.materializers.md#zenml.integrations.scipy.materializers.sparse_materializer.SparseMaterializer.ASSOCIATED_TYPES)
      * [`SparseMaterializer.extract_metadata()`](zenml.integrations.scipy.materializers.md#zenml.integrations.scipy.materializers.sparse_materializer.SparseMaterializer.extract_metadata)
      * [`SparseMaterializer.load()`](zenml.integrations.scipy.materializers.md#zenml.integrations.scipy.materializers.sparse_materializer.SparseMaterializer.load)
      * [`SparseMaterializer.save()`](zenml.integrations.scipy.materializers.md#zenml.integrations.scipy.materializers.sparse_materializer.SparseMaterializer.save)
  * [Module contents](zenml.integrations.scipy.materializers.md#module-zenml.integrations.scipy.materializers)

## Module contents

Initialization of the Scipy integration.

### *class* zenml.integrations.scipy.ScipyIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of scipy integration for ZenML.

#### NAME *= 'scipy'*

#### REQUIREMENTS *: List[str]* *= ['scipy']*

#### *classmethod* activate() → None

Activates the integration.
