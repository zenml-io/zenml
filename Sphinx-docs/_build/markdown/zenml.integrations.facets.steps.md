# zenml.integrations.facets.steps package

## Submodules

## zenml.integrations.facets.steps.facets_visualization_steps module

Facets Standard Steps.

## Module contents

Facets Standard Steps.

### *class* zenml.integrations.facets.steps.FacetsComparison(\*, datasets: List[Dict[str, str | DataFrame]])

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
