# zenml.integrations.facets package

## Subpackages

* [zenml.integrations.facets.materializers package](zenml.integrations.facets.materializers.md)
  * [Submodules](zenml.integrations.facets.materializers.md#submodules)
  * [zenml.integrations.facets.materializers.facets_materializer module](zenml.integrations.facets.materializers.md#zenml-integrations-facets-materializers-facets-materializer-module)
  * [Module contents](zenml.integrations.facets.materializers.md#module-contents)
* [zenml.integrations.facets.steps package](zenml.integrations.facets.steps.md)
  * [Submodules](zenml.integrations.facets.steps.md#submodules)
  * [zenml.integrations.facets.steps.facets_visualization_steps module](zenml.integrations.facets.steps.md#module-zenml.integrations.facets.steps.facets_visualization_steps)
  * [Module contents](zenml.integrations.facets.steps.md#module-zenml.integrations.facets.steps)
    * [`FacetsComparison`](zenml.integrations.facets.steps.md#zenml.integrations.facets.steps.FacetsComparison)
      * [`FacetsComparison.datasets`](zenml.integrations.facets.steps.md#zenml.integrations.facets.steps.FacetsComparison.datasets)
      * [`FacetsComparison.model_computed_fields`](zenml.integrations.facets.steps.md#zenml.integrations.facets.steps.FacetsComparison.model_computed_fields)
      * [`FacetsComparison.model_config`](zenml.integrations.facets.steps.md#zenml.integrations.facets.steps.FacetsComparison.model_config)
      * [`FacetsComparison.model_fields`](zenml.integrations.facets.steps.md#zenml.integrations.facets.steps.FacetsComparison.model_fields)

## Submodules

## zenml.integrations.facets.models module

Models used by the Facets integration.

### *class* zenml.integrations.facets.models.FacetsComparison(\*, datasets: List[Dict[str, str | DataFrame]])

Bases: `BaseModel`

Facets comparison model.

Returning this from any step will automatically visualize the datasets
statistics using Facets.

Attributes:
: datasets: List of datasets to compare. Should be in the format
  : [{“name”: “dataset_name”, “table”: pd.DataFrame}, …].

#### datasets *: List[Dict[str, str | DataFrame]]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'arbitrary_types_allowed': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'datasets': FieldInfo(annotation=List[Dict[str, Union[str, DataFrame]]], required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## Module contents

Facets integration for ZenML.

### *class* zenml.integrations.facets.FacetsIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Facets integration for ZenML.

#### NAME *= 'facets'*

#### REQUIREMENTS *: List[str]* *= ['facets-overview>=1.0.0']*

#### REQUIREMENTS_IGNORED_ON_UNINSTALL *: List[str]* *= ['pandas']*

#### *classmethod* activate() → None

Activate the Facets integration.

#### *classmethod* get_requirements(target_os: str | None = None) → List[str]

Method to get the requirements for the integration.

Args:
: target_os: The target operating system to get the requirements for.

Returns:
: A list of requirements.
