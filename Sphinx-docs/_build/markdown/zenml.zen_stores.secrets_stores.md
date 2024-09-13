# zenml.zen_stores.secrets_stores package

## Submodules

## zenml.zen_stores.secrets_stores.aws_secrets_store module

## zenml.zen_stores.secrets_stores.azure_secrets_store module

## zenml.zen_stores.secrets_stores.base_secrets_store module

Base Secrets Store implementation.

### *class* zenml.zen_stores.secrets_stores.base_secrets_store.BaseSecretsStore(zen_store: [BaseZenStore](zenml.zen_stores.md#zenml.zen_stores.base_zen_store.BaseZenStore), \*, config: [SecretsStoreConfiguration](zenml.config.md#zenml.config.secrets_store_config.SecretsStoreConfiguration))

Bases: `BaseModel`, [`SecretsStoreInterface`](#zenml.zen_stores.secrets_stores.secrets_store_interface.SecretsStoreInterface), `ABC`

Base class for accessing and persisting ZenML secret values.

Attributes:
: config: The configuration of the secret store.
  \_zen_store: The ZenML store that owns this secrets store.

#### CONFIG_TYPE *: ClassVar[Type[[SecretsStoreConfiguration](zenml.config.md#zenml.config.secrets_store_config.SecretsStoreConfiguration)]]*

#### TYPE *: ClassVar[[SecretsStoreType](zenml.md#zenml.enums.SecretsStoreType)]*

#### config *: [SecretsStoreConfiguration](zenml.config.md#zenml.config.secrets_store_config.SecretsStoreConfiguration)*

#### *classmethod* convert_config(data: Any, validation_info: ValidationInfo) → Any

Wrapper method to handle the raw data.

Args:
: cls: the class handler
  data: the raw input data
  validation_info: the context of the validation.

Returns:
: the validated data

#### *static* create_store(config: [SecretsStoreConfiguration](zenml.config.md#zenml.config.secrets_store_config.SecretsStoreConfiguration), \*\*kwargs: Any) → [BaseSecretsStore](#zenml.zen_stores.secrets_stores.base_secrets_store.BaseSecretsStore)

Create and initialize a secrets store from a secrets store configuration.

Args:
: config: The secrets store configuration to use.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Additional keyword arguments to pass to the store class

Returns:
: The initialized secrets store.

#### *static* get_store_class(store_config: [SecretsStoreConfiguration](zenml.config.md#zenml.config.secrets_store_config.SecretsStoreConfiguration)) → Type[[BaseSecretsStore](#zenml.zen_stores.secrets_stores.base_secrets_store.BaseSecretsStore)]

Returns the class of the given secrets store type.

Args:
: store_config: The configuration of the secrets store.

Returns:
: The class corresponding to the configured secrets store or None if
  the type is unknown.

Raises:
: TypeError: If the secrets store type is unsupported.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config': FieldInfo(annotation=SecretsStoreConfiguration, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

This function is meant to behave like a BaseModel method to initialise private attributes.

It takes context as an argument since that’s what pydantic-core passes when calling it.

Args:
: self: The BaseModel instance.
  context: The context.

#### *property* type *: [SecretsStoreType](zenml.md#zenml.enums.SecretsStoreType)*

The type of the secrets store.

Returns:
: The type of the secrets store.

#### *property* zen_store *: [BaseZenStore](zenml.zen_stores.md#zenml.zen_stores.base_zen_store.BaseZenStore)*

The ZenML store that owns this secrets store.

Returns:
: The ZenML store that owns this secrets store.

Raises:
: ValueError: If the store is not initialized.

## zenml.zen_stores.secrets_stores.gcp_secrets_store module

## zenml.zen_stores.secrets_stores.hashicorp_secrets_store module

## zenml.zen_stores.secrets_stores.secrets_store_interface module

ZenML secrets store interface.

### *class* zenml.zen_stores.secrets_stores.secrets_store_interface.SecretsStoreInterface

Bases: `ABC`

ZenML secrets store interface.

All ZenML secrets stores must implement the methods in this interface.

#### *abstract* delete_secret_values(secret_id: UUID) → None

Deletes secret values for an existing secret.

Args:
: secret_id: The ID of the secret.

Raises:
: KeyError: if no secret values for the given ID are stored in the
  : secrets store.

#### *abstract* get_secret_values(secret_id: UUID) → Dict[str, str]

Get the secret values for an existing secret.

Args:
: secret_id: ID of the secret.

Returns:
: The secret values.

Raises:
: KeyError: if no secret values for the given ID are stored in the
  : secrets store.

#### *abstract* store_secret_values(secret_id: UUID, secret_values: Dict[str, str]) → None

Store secret values for a new secret.

Args:
: secret_id: ID of the secret.
  secret_values: Values for the secret.

#### *abstract* update_secret_values(secret_id: UUID, secret_values: Dict[str, str]) → None

Updates secret values for an existing secret.

Args:
: secret_id: The ID of the secret to be updated.
  secret_values: The new secret values.

Raises:
: KeyError: if no secret values for the given ID are stored in the
  : secrets store.

## zenml.zen_stores.secrets_stores.service_connector_secrets_store module

## zenml.zen_stores.secrets_stores.sql_secrets_store module

SQL Secrets Store implementation.

### *class* zenml.zen_stores.secrets_stores.sql_secrets_store.SqlSecretsStore(zen_store: [BaseZenStore](zenml.zen_stores.md#zenml.zen_stores.base_zen_store.BaseZenStore), \*, config: [SqlSecretsStoreConfiguration](#zenml.zen_stores.secrets_stores.sql_secrets_store.SqlSecretsStoreConfiguration))

Bases: [`BaseSecretsStore`](#zenml.zen_stores.secrets_stores.base_secrets_store.BaseSecretsStore)

Secrets store implementation that uses the SQL ZenML store as a backend.

This secrets store piggybacks on the SQL ZenML store. It uses the same
database and configuration as the SQL ZenML store.

Attributes:
: config: The configuration of the SQL secrets store.
  TYPE: The type of the store.
  CONFIG_TYPE: The type of the store configuration.

#### CONFIG_TYPE

alias of [`SqlSecretsStoreConfiguration`](#zenml.zen_stores.secrets_stores.sql_secrets_store.SqlSecretsStoreConfiguration)

#### TYPE *: ClassVar[[SecretsStoreType](zenml.md#zenml.enums.SecretsStoreType)]* *= 'sql'*

#### config *: [SqlSecretsStoreConfiguration](#zenml.zen_stores.secrets_stores.sql_secrets_store.SqlSecretsStoreConfiguration)*

#### delete_secret_values(secret_id: UUID) → None

Deletes secret values for an existing secret.

Args:
: secret_id: The ID of the secret.

Raises:
: KeyError: if no secret values for the given ID are stored in the
  : secrets store.

#### *property* engine *: Engine*

The SQLAlchemy engine.

Returns:
: The SQLAlchemy engine.

#### get_secret_values(secret_id: UUID) → Dict[str, str]

Get the secret values for an existing secret.

Args:
: secret_id: ID of the secret.

Returns:
: The secret values.

Raises:
: KeyError: if no secret values for the given ID are stored in the
  : secrets store.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config': FieldInfo(annotation=SqlSecretsStoreConfiguration, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### store_secret_values(secret_id: UUID, secret_values: Dict[str, str]) → None

Store secret values for a new secret.

The secret is already created in the database by the SQL Zen store, this
method only stores the secret values.

Args:
: secret_id: ID of the secret.
  secret_values: Values for the secret.

Raises:
: KeyError: if a secret for the given ID is not found.

#### update_secret_values(secret_id: UUID, secret_values: Dict[str, str]) → None

Updates secret values for an existing secret.

Args:
: secret_id: The ID of the secret to be updated.
  secret_values: The new secret values.

#### *property* zen_store *: [SqlZenStore](zenml.zen_stores.md#zenml.zen_stores.sql_zen_store.SqlZenStore)*

The ZenML store that this SQL secrets store is using as a back-end.

Returns:
: The ZenML store that this SQL secrets store is using as a back-end.

Raises:
: ValueError: If the store is not initialized.

### *class* zenml.zen_stores.secrets_stores.sql_secrets_store.SqlSecretsStoreConfiguration(\*, type: [SecretsStoreType](zenml.md#zenml.enums.SecretsStoreType) = SecretsStoreType.SQL, class_path: str | None = None, encryption_key: str | None = None)

Bases: [`SecretsStoreConfiguration`](zenml.config.md#zenml.config.secrets_store_config.SecretsStoreConfiguration)

SQL secrets store configuration.

Attributes:
: type: The type of the store.
  encryption_key: The encryption key to use for the SQL secrets store.
  <br/>
  > If not set, the passwords will not be encrypted in the database.

#### encryption_key *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'validate_assignment': False}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'class_path': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'encryption_key': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'type': FieldInfo(annotation=SecretsStoreType, required=False, default=<SecretsStoreType.SQL: 'sql'>)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: [SecretsStoreType](zenml.md#zenml.enums.SecretsStoreType)*

## Module contents

Centralized secrets management.
