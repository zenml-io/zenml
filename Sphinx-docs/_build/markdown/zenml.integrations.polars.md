# zenml.integrations.polars package

## Subpackages

* [zenml.integrations.polars.materializers package](zenml.integrations.polars.materializers.md)
  * [Submodules](zenml.integrations.polars.materializers.md#submodules)
  * [zenml.integrations.polars.materializers.dataframe_materializer module](zenml.integrations.polars.materializers.md#zenml-integrations-polars-materializers-dataframe-materializer-module)
  * [Module contents](zenml.integrations.polars.materializers.md#module-contents)

## Module contents

Initialization of the Polars integration.

### *class* zenml.integrations.polars.PolarsIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Polars integration for ZenML.

#### NAME *= 'polars'*

#### REQUIREMENTS *: List[str]* *= ['polars>=0.19.5', 'pyarrow>=12.0.0']*

#### REQUIREMENTS_IGNORED_ON_UNINSTALL *: List[str]* *= ['pyarrow']*

#### *classmethod* activate() → None

Activates the integration.
