# zenml.secret package

## Subpackages

* [zenml.secret.schemas package](zenml.secret.schemas.md)
  * [Submodules](zenml.secret.schemas.md#submodules)
  * [zenml.secret.schemas.aws_secret_schema module](zenml.secret.schemas.md#module-zenml.secret.schemas.aws_secret_schema)
    * [`AWSSecretSchema`](zenml.secret.schemas.md#zenml.secret.schemas.aws_secret_schema.AWSSecretSchema)
      * [`AWSSecretSchema.aws_access_key_id`](zenml.secret.schemas.md#zenml.secret.schemas.aws_secret_schema.AWSSecretSchema.aws_access_key_id)
      * [`AWSSecretSchema.aws_secret_access_key`](zenml.secret.schemas.md#zenml.secret.schemas.aws_secret_schema.AWSSecretSchema.aws_secret_access_key)
      * [`AWSSecretSchema.aws_session_token`](zenml.secret.schemas.md#zenml.secret.schemas.aws_secret_schema.AWSSecretSchema.aws_session_token)
      * [`AWSSecretSchema.model_computed_fields`](zenml.secret.schemas.md#zenml.secret.schemas.aws_secret_schema.AWSSecretSchema.model_computed_fields)
      * [`AWSSecretSchema.model_config`](zenml.secret.schemas.md#zenml.secret.schemas.aws_secret_schema.AWSSecretSchema.model_config)
      * [`AWSSecretSchema.model_fields`](zenml.secret.schemas.md#zenml.secret.schemas.aws_secret_schema.AWSSecretSchema.model_fields)
  * [zenml.secret.schemas.azure_secret_schema module](zenml.secret.schemas.md#module-zenml.secret.schemas.azure_secret_schema)
    * [`AzureSecretSchema`](zenml.secret.schemas.md#zenml.secret.schemas.azure_secret_schema.AzureSecretSchema)
      * [`AzureSecretSchema.account_key`](zenml.secret.schemas.md#zenml.secret.schemas.azure_secret_schema.AzureSecretSchema.account_key)
      * [`AzureSecretSchema.account_name`](zenml.secret.schemas.md#zenml.secret.schemas.azure_secret_schema.AzureSecretSchema.account_name)
      * [`AzureSecretSchema.client_id`](zenml.secret.schemas.md#zenml.secret.schemas.azure_secret_schema.AzureSecretSchema.client_id)
      * [`AzureSecretSchema.client_secret`](zenml.secret.schemas.md#zenml.secret.schemas.azure_secret_schema.AzureSecretSchema.client_secret)
      * [`AzureSecretSchema.connection_string`](zenml.secret.schemas.md#zenml.secret.schemas.azure_secret_schema.AzureSecretSchema.connection_string)
      * [`AzureSecretSchema.model_computed_fields`](zenml.secret.schemas.md#zenml.secret.schemas.azure_secret_schema.AzureSecretSchema.model_computed_fields)
      * [`AzureSecretSchema.model_config`](zenml.secret.schemas.md#zenml.secret.schemas.azure_secret_schema.AzureSecretSchema.model_config)
      * [`AzureSecretSchema.model_fields`](zenml.secret.schemas.md#zenml.secret.schemas.azure_secret_schema.AzureSecretSchema.model_fields)
      * [`AzureSecretSchema.sas_token`](zenml.secret.schemas.md#zenml.secret.schemas.azure_secret_schema.AzureSecretSchema.sas_token)
      * [`AzureSecretSchema.tenant_id`](zenml.secret.schemas.md#zenml.secret.schemas.azure_secret_schema.AzureSecretSchema.tenant_id)
  * [zenml.secret.schemas.basic_auth_secret_schema module](zenml.secret.schemas.md#module-zenml.secret.schemas.basic_auth_secret_schema)
    * [`BasicAuthSecretSchema`](zenml.secret.schemas.md#zenml.secret.schemas.basic_auth_secret_schema.BasicAuthSecretSchema)
      * [`BasicAuthSecretSchema.model_computed_fields`](zenml.secret.schemas.md#zenml.secret.schemas.basic_auth_secret_schema.BasicAuthSecretSchema.model_computed_fields)
      * [`BasicAuthSecretSchema.model_config`](zenml.secret.schemas.md#zenml.secret.schemas.basic_auth_secret_schema.BasicAuthSecretSchema.model_config)
      * [`BasicAuthSecretSchema.model_fields`](zenml.secret.schemas.md#zenml.secret.schemas.basic_auth_secret_schema.BasicAuthSecretSchema.model_fields)
      * [`BasicAuthSecretSchema.password`](zenml.secret.schemas.md#zenml.secret.schemas.basic_auth_secret_schema.BasicAuthSecretSchema.password)
      * [`BasicAuthSecretSchema.username`](zenml.secret.schemas.md#zenml.secret.schemas.basic_auth_secret_schema.BasicAuthSecretSchema.username)
  * [zenml.secret.schemas.gcp_secret_schema module](zenml.secret.schemas.md#module-zenml.secret.schemas.gcp_secret_schema)
    * [`GCPSecretSchema`](zenml.secret.schemas.md#zenml.secret.schemas.gcp_secret_schema.GCPSecretSchema)
      * [`GCPSecretSchema.get_credential_dict()`](zenml.secret.schemas.md#zenml.secret.schemas.gcp_secret_schema.GCPSecretSchema.get_credential_dict)
      * [`GCPSecretSchema.model_computed_fields`](zenml.secret.schemas.md#zenml.secret.schemas.gcp_secret_schema.GCPSecretSchema.model_computed_fields)
      * [`GCPSecretSchema.model_config`](zenml.secret.schemas.md#zenml.secret.schemas.gcp_secret_schema.GCPSecretSchema.model_config)
      * [`GCPSecretSchema.model_fields`](zenml.secret.schemas.md#zenml.secret.schemas.gcp_secret_schema.GCPSecretSchema.model_fields)
      * [`GCPSecretSchema.token`](zenml.secret.schemas.md#zenml.secret.schemas.gcp_secret_schema.GCPSecretSchema.token)
  * [Module contents](zenml.secret.schemas.md#module-zenml.secret.schemas)
    * [`AWSSecretSchema`](zenml.secret.schemas.md#zenml.secret.schemas.AWSSecretSchema)
      * [`AWSSecretSchema.aws_access_key_id`](zenml.secret.schemas.md#zenml.secret.schemas.AWSSecretSchema.aws_access_key_id)
      * [`AWSSecretSchema.aws_secret_access_key`](zenml.secret.schemas.md#zenml.secret.schemas.AWSSecretSchema.aws_secret_access_key)
      * [`AWSSecretSchema.aws_session_token`](zenml.secret.schemas.md#zenml.secret.schemas.AWSSecretSchema.aws_session_token)
      * [`AWSSecretSchema.model_computed_fields`](zenml.secret.schemas.md#zenml.secret.schemas.AWSSecretSchema.model_computed_fields)
      * [`AWSSecretSchema.model_config`](zenml.secret.schemas.md#zenml.secret.schemas.AWSSecretSchema.model_config)
      * [`AWSSecretSchema.model_fields`](zenml.secret.schemas.md#zenml.secret.schemas.AWSSecretSchema.model_fields)
    * [`AzureSecretSchema`](zenml.secret.schemas.md#zenml.secret.schemas.AzureSecretSchema)
      * [`AzureSecretSchema.account_key`](zenml.secret.schemas.md#zenml.secret.schemas.AzureSecretSchema.account_key)
      * [`AzureSecretSchema.account_name`](zenml.secret.schemas.md#zenml.secret.schemas.AzureSecretSchema.account_name)
      * [`AzureSecretSchema.client_id`](zenml.secret.schemas.md#zenml.secret.schemas.AzureSecretSchema.client_id)
      * [`AzureSecretSchema.client_secret`](zenml.secret.schemas.md#zenml.secret.schemas.AzureSecretSchema.client_secret)
      * [`AzureSecretSchema.connection_string`](zenml.secret.schemas.md#zenml.secret.schemas.AzureSecretSchema.connection_string)
      * [`AzureSecretSchema.model_computed_fields`](zenml.secret.schemas.md#zenml.secret.schemas.AzureSecretSchema.model_computed_fields)
      * [`AzureSecretSchema.model_config`](zenml.secret.schemas.md#zenml.secret.schemas.AzureSecretSchema.model_config)
      * [`AzureSecretSchema.model_fields`](zenml.secret.schemas.md#zenml.secret.schemas.AzureSecretSchema.model_fields)
      * [`AzureSecretSchema.sas_token`](zenml.secret.schemas.md#zenml.secret.schemas.AzureSecretSchema.sas_token)
      * [`AzureSecretSchema.tenant_id`](zenml.secret.schemas.md#zenml.secret.schemas.AzureSecretSchema.tenant_id)
    * [`BasicAuthSecretSchema`](zenml.secret.schemas.md#zenml.secret.schemas.BasicAuthSecretSchema)
      * [`BasicAuthSecretSchema.model_computed_fields`](zenml.secret.schemas.md#zenml.secret.schemas.BasicAuthSecretSchema.model_computed_fields)
      * [`BasicAuthSecretSchema.model_config`](zenml.secret.schemas.md#zenml.secret.schemas.BasicAuthSecretSchema.model_config)
      * [`BasicAuthSecretSchema.model_fields`](zenml.secret.schemas.md#zenml.secret.schemas.BasicAuthSecretSchema.model_fields)
      * [`BasicAuthSecretSchema.password`](zenml.secret.schemas.md#zenml.secret.schemas.BasicAuthSecretSchema.password)
      * [`BasicAuthSecretSchema.username`](zenml.secret.schemas.md#zenml.secret.schemas.BasicAuthSecretSchema.username)
    * [`GCPSecretSchema`](zenml.secret.schemas.md#zenml.secret.schemas.GCPSecretSchema)
      * [`GCPSecretSchema.get_credential_dict()`](zenml.secret.schemas.md#zenml.secret.schemas.GCPSecretSchema.get_credential_dict)
      * [`GCPSecretSchema.model_computed_fields`](zenml.secret.schemas.md#zenml.secret.schemas.GCPSecretSchema.model_computed_fields)
      * [`GCPSecretSchema.model_config`](zenml.secret.schemas.md#zenml.secret.schemas.GCPSecretSchema.model_config)
      * [`GCPSecretSchema.model_fields`](zenml.secret.schemas.md#zenml.secret.schemas.GCPSecretSchema.model_fields)
      * [`GCPSecretSchema.token`](zenml.secret.schemas.md#zenml.secret.schemas.GCPSecretSchema.token)

## Submodules

## zenml.secret.base_secret module

Implementation of the Base SecretSchema class.

### *class* zenml.secret.base_secret.BaseSecretSchema

Bases: `BaseModel`

Base class for all Secret Schemas.

#### *classmethod* get_schema_keys() → List[str]

Get all attributes that are part of the schema.

These schema keys can be used to define all required key-value pairs of
a secret schema.

Returns:
: A list of all attribute names that are part of the schema.

#### get_values() → Dict[str, Any]

Get all values of the secret schema.

Returns:
: A dictionary of all attribute names and their corresponding values.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## Module contents

Initialization of the ZenML Secret module.

A ZenML Secret is a grouping of key-value pairs. These are accessed and
administered via the ZenML Secret Store.

### *class* zenml.secret.BaseSecretSchema

Bases: `BaseModel`

Base class for all Secret Schemas.

#### *classmethod* get_schema_keys() → List[str]

Get all attributes that are part of the schema.

These schema keys can be used to define all required key-value pairs of
a secret schema.

Returns:
: A list of all attribute names that are part of the schema.

#### get_values() → Dict[str, Any]

Get all values of the secret schema.

Returns:
: A dictionary of all attribute names and their corresponding values.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.
