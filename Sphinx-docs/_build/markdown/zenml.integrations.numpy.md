# zenml.integrations.numpy package

## Subpackages

* [zenml.integrations.numpy.materializers package](zenml.integrations.numpy.materializers.md)
  * [Submodules](zenml.integrations.numpy.materializers.md#submodules)
  * [zenml.integrations.numpy.materializers.numpy_materializer module](zenml.integrations.numpy.materializers.md#module-zenml.integrations.numpy.materializers.numpy_materializer)
    * [`NumpyMaterializer`](zenml.integrations.numpy.materializers.md#zenml.integrations.numpy.materializers.numpy_materializer.NumpyMaterializer)
      * [`NumpyMaterializer.ASSOCIATED_ARTIFACT_TYPE`](zenml.integrations.numpy.materializers.md#zenml.integrations.numpy.materializers.numpy_materializer.NumpyMaterializer.ASSOCIATED_ARTIFACT_TYPE)
      * [`NumpyMaterializer.ASSOCIATED_TYPES`](zenml.integrations.numpy.materializers.md#zenml.integrations.numpy.materializers.numpy_materializer.NumpyMaterializer.ASSOCIATED_TYPES)
      * [`NumpyMaterializer.extract_metadata()`](zenml.integrations.numpy.materializers.md#zenml.integrations.numpy.materializers.numpy_materializer.NumpyMaterializer.extract_metadata)
      * [`NumpyMaterializer.load()`](zenml.integrations.numpy.materializers.md#zenml.integrations.numpy.materializers.numpy_materializer.NumpyMaterializer.load)
      * [`NumpyMaterializer.save()`](zenml.integrations.numpy.materializers.md#zenml.integrations.numpy.materializers.numpy_materializer.NumpyMaterializer.save)
      * [`NumpyMaterializer.save_visualizations()`](zenml.integrations.numpy.materializers.md#zenml.integrations.numpy.materializers.numpy_materializer.NumpyMaterializer.save_visualizations)
  * [Module contents](zenml.integrations.numpy.materializers.md#module-zenml.integrations.numpy.materializers)

## Module contents

Initialization of the Numpy integration.

### *class* zenml.integrations.numpy.NumpyIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Numpy integration for ZenML.

#### NAME *= 'numpy'*

#### REQUIREMENTS *: List[str]* *= ['numpy<2.0.0']*

#### *classmethod* activate() → None

Activates the integration.
