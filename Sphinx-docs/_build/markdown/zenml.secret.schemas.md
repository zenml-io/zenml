# zenml.secret.schemas package

## Submodules

## zenml.secret.schemas.aws_secret_schema module

AWS Authentication Secret Schema definition.

### *class* zenml.secret.schemas.aws_secret_schema.AWSSecretSchema(\*, aws_access_key_id: str, aws_secret_access_key: str, aws_session_token: str | None = None)

Bases: [`BaseSecretSchema`](zenml.secret.md#zenml.secret.base_secret.BaseSecretSchema)

AWS Authentication Secret Schema definition.

#### aws_access_key_id *: str*

#### aws_secret_access_key *: str*

#### aws_session_token *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'aws_access_key_id': FieldInfo(annotation=str, required=True), 'aws_secret_access_key': FieldInfo(annotation=str, required=True), 'aws_session_token': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## zenml.secret.schemas.azure_secret_schema module

Azure Authentication Secret Schema definition.

### *class* zenml.secret.schemas.azure_secret_schema.AzureSecretSchema(\*, account_name: str | None = None, account_key: str | None = None, sas_token: str | None = None, connection_string: str | None = None, client_id: str | None = None, client_secret: str | None = None, tenant_id: str | None = None)

Bases: [`BaseSecretSchema`](zenml.secret.md#zenml.secret.base_secret.BaseSecretSchema)

Azure Authentication Secret Schema definition.

#### account_key *: str | None*

#### account_name *: str | None*

#### client_id *: str | None*

#### client_secret *: str | None*

#### connection_string *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'account_key': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'account_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'client_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'client_secret': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'connection_string': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'sas_token': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'tenant_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### sas_token *: str | None*

#### tenant_id *: str | None*

## zenml.secret.schemas.basic_auth_secret_schema module

Basic Authentication Secret Schema definition.

### *class* zenml.secret.schemas.basic_auth_secret_schema.BasicAuthSecretSchema(\*, username: str, password: str)

Bases: [`BaseSecretSchema`](zenml.secret.md#zenml.secret.base_secret.BaseSecretSchema)

Secret schema for basic authentication.

Attributes:
: username: The username that should be used for authentication.
  password: The password that should be used for authentication.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'password': FieldInfo(annotation=str, required=True), 'username': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### password *: str*

#### username *: str*

## zenml.secret.schemas.gcp_secret_schema module

GCP Authentication Secret Schema definition.

### *class* zenml.secret.schemas.gcp_secret_schema.GCPSecretSchema(\*, token: str)

Bases: [`BaseSecretSchema`](zenml.secret.md#zenml.secret.base_secret.BaseSecretSchema)

GCP Authentication Secret Schema definition.

#### get_credential_dict() → Dict[str, Any]

Gets a dictionary of credentials for authenticating to GCP.

Returns:
: A dictionary representing GCP credentials.

Raises:
: ValueError: If the token value is not a JSON string of a dictionary.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'token': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### token *: str*

## Module contents

Initialization of secret schemas.

### *class* zenml.secret.schemas.AWSSecretSchema(\*, aws_access_key_id: str, aws_secret_access_key: str, aws_session_token: str | None = None)

Bases: [`BaseSecretSchema`](zenml.secret.md#zenml.secret.base_secret.BaseSecretSchema)

AWS Authentication Secret Schema definition.

#### aws_access_key_id *: str*

#### aws_secret_access_key *: str*

#### aws_session_token *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'aws_access_key_id': FieldInfo(annotation=str, required=True), 'aws_secret_access_key': FieldInfo(annotation=str, required=True), 'aws_session_token': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.secret.schemas.AzureSecretSchema(\*, account_name: str | None = None, account_key: str | None = None, sas_token: str | None = None, connection_string: str | None = None, client_id: str | None = None, client_secret: str | None = None, tenant_id: str | None = None)

Bases: [`BaseSecretSchema`](zenml.secret.md#zenml.secret.base_secret.BaseSecretSchema)

Azure Authentication Secret Schema definition.

#### account_key *: str | None*

#### account_name *: str | None*

#### client_id *: str | None*

#### client_secret *: str | None*

#### connection_string *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'account_key': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'account_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'client_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'client_secret': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'connection_string': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'sas_token': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'tenant_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### sas_token *: str | None*

#### tenant_id *: str | None*

### *class* zenml.secret.schemas.BasicAuthSecretSchema(\*, username: str, password: str)

Bases: [`BaseSecretSchema`](zenml.secret.md#zenml.secret.base_secret.BaseSecretSchema)

Secret schema for basic authentication.

Attributes:
: username: The username that should be used for authentication.
  password: The password that should be used for authentication.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'password': FieldInfo(annotation=str, required=True), 'username': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### password *: str*

#### username *: str*

### *class* zenml.secret.schemas.GCPSecretSchema(\*, token: str)

Bases: [`BaseSecretSchema`](zenml.secret.md#zenml.secret.base_secret.BaseSecretSchema)

GCP Authentication Secret Schema definition.

#### get_credential_dict() → Dict[str, Any]

Gets a dictionary of credentials for authenticating to GCP.

Returns:
: A dictionary representing GCP credentials.

Raises:
: ValueError: If the token value is not a JSON string of a dictionary.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'token': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### token *: str*
