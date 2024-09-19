# zenml.integrations.pandas package

## Subpackages

* [zenml.integrations.pandas.materializers package](zenml.integrations.pandas.materializers.md)
  * [Submodules](zenml.integrations.pandas.materializers.md#submodules)
  * [zenml.integrations.pandas.materializers.pandas_materializer module](zenml.integrations.pandas.materializers.md#module-zenml.integrations.pandas.materializers.pandas_materializer)
    * [`PandasMaterializer`](zenml.integrations.pandas.materializers.md#zenml.integrations.pandas.materializers.pandas_materializer.PandasMaterializer)
      * [`PandasMaterializer.ASSOCIATED_ARTIFACT_TYPE`](zenml.integrations.pandas.materializers.md#zenml.integrations.pandas.materializers.pandas_materializer.PandasMaterializer.ASSOCIATED_ARTIFACT_TYPE)
      * [`PandasMaterializer.ASSOCIATED_TYPES`](zenml.integrations.pandas.materializers.md#zenml.integrations.pandas.materializers.pandas_materializer.PandasMaterializer.ASSOCIATED_TYPES)
      * [`PandasMaterializer.extract_metadata()`](zenml.integrations.pandas.materializers.md#zenml.integrations.pandas.materializers.pandas_materializer.PandasMaterializer.extract_metadata)
      * [`PandasMaterializer.load()`](zenml.integrations.pandas.materializers.md#zenml.integrations.pandas.materializers.pandas_materializer.PandasMaterializer.load)
      * [`PandasMaterializer.save()`](zenml.integrations.pandas.materializers.md#zenml.integrations.pandas.materializers.pandas_materializer.PandasMaterializer.save)
      * [`PandasMaterializer.save_visualizations()`](zenml.integrations.pandas.materializers.md#zenml.integrations.pandas.materializers.pandas_materializer.PandasMaterializer.save_visualizations)
  * [Module contents](zenml.integrations.pandas.materializers.md#module-zenml.integrations.pandas.materializers)

## Module contents

Initialization of the Pandas integration.

### *class* zenml.integrations.pandas.PandasIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Pandas integration for ZenML.

#### NAME *= 'pandas'*

#### REQUIREMENTS *: List[str]* *= ['pandas>=2.0.0']*

#### *classmethod* activate() → None

Activates the integration.
