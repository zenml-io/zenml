# zenml.integrations.whylogs.secret_schemas package

## Submodules

## zenml.integrations.whylogs.secret_schemas.whylabs_secret_schema module

Implementation for Seldon secret schemas.

### *class* zenml.integrations.whylogs.secret_schemas.whylabs_secret_schema.WhylabsSecretSchema(\*, whylabs_default_org_id: str, whylabs_api_key: str, whylabs_default_dataset_id: str | None = None)

Bases: [`BaseSecretSchema`](zenml.secret.md#zenml.secret.base_secret.BaseSecretSchema)

Whylabs credentials.

Attributes:
: whylabs_default_org_id: the Whylabs organization ID.
  whylabs_api_key: Whylabs API key.
  whylabs_default_dataset_id: default Whylabs dataset ID to use when
  <br/>
  > logging data profiles.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'whylabs_api_key': FieldInfo(annotation=str, required=True), 'whylabs_default_dataset_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'whylabs_default_org_id': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### whylabs_api_key *: str*

#### whylabs_default_dataset_id *: str | None*

#### whylabs_default_org_id *: str*

## Module contents

Initialization for the Whylabs secret schema.

This schema can be used to configure a ZenML secret to authenticate ZenML to
use the Whylabs platform to automatically log all whylogs data profiles
generated and by pipeline steps.

### *class* zenml.integrations.whylogs.secret_schemas.WhylabsSecretSchema(\*, whylabs_default_org_id: str, whylabs_api_key: str, whylabs_default_dataset_id: str | None = None)

Bases: [`BaseSecretSchema`](zenml.secret.md#zenml.secret.base_secret.BaseSecretSchema)

Whylabs credentials.

Attributes:
: whylabs_default_org_id: the Whylabs organization ID.
  whylabs_api_key: Whylabs API key.
  whylabs_default_dataset_id: default Whylabs dataset ID to use when
  <br/>
  > logging data profiles.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'whylabs_api_key': FieldInfo(annotation=str, required=True), 'whylabs_default_dataset_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'whylabs_default_org_id': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### whylabs_api_key *: str*

#### whylabs_default_dataset_id *: str | None*

#### whylabs_default_org_id *: str*
