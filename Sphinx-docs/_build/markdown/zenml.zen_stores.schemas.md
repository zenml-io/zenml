# zenml.zen_stores.schemas package

## Submodules

## zenml.zen_stores.schemas.action_schemas module

SQL Model Implementations for Actions.

### *class* zenml.zen_stores.schemas.action_schemas.ActionSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, workspace_id: UUID, user_id: UUID | None, service_account_id: UUID, auth_window: int, flavor: str, plugin_subtype: str, description: str | None, configuration: bytes)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for actions.

#### auth_window *: int*

#### configuration *: bytes*

#### created *: datetime*

#### description *: str | None*

#### flavor *: str*

#### *classmethod* from_request(request: [ActionRequest](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionRequest)) → [ActionSchema](#zenml.zen_stores.schemas.action_schemas.ActionSchema)

Convert a ActionRequest to a ActionSchema.

Args:
: request: The request model to convert.

Returns:
: The converted schema.

#### id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'auth_window': FieldInfo(annotation=int, required=True), 'configuration': FieldInfo(annotation=bytes, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'description': FieldInfo(annotation=Union[str, NoneType], required=True), 'flavor': FieldInfo(annotation=str, required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'name': FieldInfo(annotation=str, required=True), 'plugin_subtype': FieldInfo(annotation=str, required=True), 'service_account_id': FieldInfo(annotation=UUID, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### plugin_subtype *: str*

#### service_account *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema)]*

#### service_account_id *: UUID*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [ActionResponse](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionResponse)

Converts the action schema to a model.

Args:
: include_metadata: Flag deciding whether to include the output model(s)
  : metadata fields in the response.
  <br/>
  include_resources: Flag deciding whether to include the output model(s)
  : metadata fields in the response.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The converted model.

#### triggers *: Mapped[List[[TriggerSchema](#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema)]]*

#### update(action_update: [ActionUpdate](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionUpdate)) → [ActionSchema](#zenml.zen_stores.schemas.action_schemas.ActionSchema)

Updates a action schema with a action update model.

Args:
: action_update: ActionUpdate to update the action with.

Returns:
: The updated ActionSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

## zenml.zen_stores.schemas.api_key_schemas module

SQLModel implementation of user tables.

### *class* zenml.zen_stores.schemas.api_key_schemas.APIKeySchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, description: str, key: str, previous_key: str | None = None, retain_period: int = 0, active: bool = True, last_login: datetime | None = None, last_rotated: datetime | None = None, service_account_id: UUID)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for API keys.

#### active *: bool*

#### created *: datetime*

#### description *: str*

#### *classmethod* from_request(service_account_id: UUID, request: [APIKeyRequest](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyRequest)) → Tuple[[APIKeySchema](#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema), str]

Convert a APIKeyRequest to a APIKeySchema.

Args:
: service_account_id: The service account id to associate the key
  : with.
  <br/>
  request: The request model to convert.

Returns:
: The converted schema and the un-hashed API key.

#### id *: UUID*

#### internal_update(update: [APIKeyInternalUpdate](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyInternalUpdate)) → [APIKeySchema](#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema)

Update an APIKeySchema with an APIKeyInternalUpdate.

The internal update can also update the last used timestamp.

Args:
: update: The update model.

Returns:
: The updated APIKeySchema.

#### key *: str*

#### last_login *: datetime | None*

#### last_rotated *: datetime | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'active': FieldInfo(annotation=bool, required=False, default=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'description': FieldInfo(annotation=str, required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'key': FieldInfo(annotation=str, required=True), 'last_login': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'last_rotated': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'name': FieldInfo(annotation=str, required=True), 'previous_key': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'retain_period': FieldInfo(annotation=int, required=False, default=0), 'service_account_id': FieldInfo(annotation=UUID, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### previous_key *: str | None*

#### retain_period *: int*

#### rotate(rotate_request: [APIKeyRotateRequest](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyRotateRequest)) → Tuple[[APIKeySchema](#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema), str]

Rotate the key for an APIKeySchema.

Args:
: rotate_request: The rotate request model.

Returns:
: The updated APIKeySchema and the new un-hashed key.

#### service_account *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema)]*

#### service_account_id *: UUID*

#### to_internal_model(hydrate: bool = False) → [APIKeyInternalResponse](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyInternalResponse)

Convert a APIKeySchema to an APIKeyInternalResponse.

The internal response model includes the hashed key values.

Args:
: hydrate: bool to decide whether to return a hydrated version of the
  : model.

Returns:
: The created APIKeyInternalResponse.

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [APIKeyResponse](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyResponse)

Convert a APIKeySchema to an APIKeyResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to filter models.

Returns:
: The created APIKeyResponse.

#### update(update: [APIKeyUpdate](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyUpdate)) → [APIKeySchema](#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema)

Update an APIKeySchema with an APIKeyUpdate.

Args:
: update: The update model.

Returns:
: The updated APIKeySchema.

#### updated *: datetime*

## zenml.zen_stores.schemas.artifact_schemas module

SQLModel implementation of artifact table.

### *class* zenml.zen_stores.schemas.artifact_schemas.ArtifactSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, has_custom_name: bool)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for artifacts.

#### created *: datetime*

#### *classmethod* from_request(artifact_request: [ArtifactRequest](zenml.models.v2.core.md#zenml.models.v2.core.artifact.ArtifactRequest)) → [ArtifactSchema](#zenml.zen_stores.schemas.artifact_schemas.ArtifactSchema)

Convert an ArtifactRequest to an ArtifactSchema.

Args:
: artifact_request: The request model to convert.

Returns:
: The converted schema.

#### has_custom_name *: bool*

#### id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'has_custom_name': FieldInfo(annotation=bool, required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'name': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### tags *: Mapped[List[[TagResourceSchema](#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema)]]*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [ArtifactResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact.ArtifactResponse)

Convert an ArtifactSchema to an ArtifactResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created ArtifactResponse.

#### update(artifact_update: [ArtifactUpdate](zenml.models.v2.core.md#zenml.models.v2.core.artifact.ArtifactUpdate)) → [ArtifactSchema](#zenml.zen_stores.schemas.artifact_schemas.ArtifactSchema)

Update an ArtifactSchema with an ArtifactUpdate.

Args:
: artifact_update: The update model to apply.

Returns:
: The updated ArtifactSchema.

#### updated *: datetime*

#### versions *: Mapped[List[[ArtifactVersionSchema](#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema)]]*

### *class* zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, version: str, version_number: int | None, type: str, uri: str, materializer: str, data_type: str, artifact_id: UUID, artifact_store_id: UUID | None, user_id: UUID | None, workspace_id: UUID)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

SQL Model for artifact versions.

#### artifact *: Mapped[[ArtifactSchema](#zenml.zen_stores.schemas.artifact_schemas.ArtifactSchema)]*

#### artifact_id *: UUID*

#### artifact_store_id *: UUID | None*

#### created *: datetime*

#### data_type *: str*

#### *classmethod* from_request(artifact_version_request: [ArtifactVersionRequest](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionRequest)) → [ArtifactVersionSchema](#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema)

Convert an ArtifactVersionRequest to an ArtifactVersionSchema.

Args:
: artifact_version_request: The request model to convert.

Returns:
: The converted schema.

#### id *: UUID*

#### input_of_step_runs *: Mapped[List[[StepRunInputArtifactSchema](#zenml.zen_stores.schemas.step_run_schemas.StepRunInputArtifactSchema)]]*

#### materializer *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact_id': FieldInfo(annotation=UUID, required=True), 'artifact_store_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'data_type': FieldInfo(annotation=str, required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'materializer': FieldInfo(annotation=str, required=True), 'type': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'uri': FieldInfo(annotation=str, required=True), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'version': FieldInfo(annotation=str, required=True), 'version_number': FieldInfo(annotation=Union[int, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_versions_artifacts_links *: Mapped[List[[ModelVersionArtifactSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema)]]*

#### output_of_step_runs *: Mapped[List[[StepRunOutputArtifactSchema](#zenml.zen_stores.schemas.step_run_schemas.StepRunOutputArtifactSchema)]]*

#### run_metadata *: Mapped[List[[RunMetadataSchema](#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema)]]*

#### tags *: Mapped[List[[TagResourceSchema](#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema)]]*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [ArtifactVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionResponse)

Convert an ArtifactVersionSchema to an ArtifactVersionResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created ArtifactVersionResponse.

#### type *: str*

#### update(artifact_version_update: [ArtifactVersionUpdate](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionUpdate)) → [ArtifactVersionSchema](#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema)

Update an ArtifactVersionSchema with an ArtifactVersionUpdate.

Args:
: artifact_version_update: The update model to apply.

Returns:
: The updated ArtifactVersionSchema.

#### updated *: datetime*

#### uri *: str*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### version *: str*

#### version_number *: int | None*

#### visualizations *: Mapped[List[[ArtifactVisualizationSchema](#zenml.zen_stores.schemas.artifact_visualization_schemas.ArtifactVisualizationSchema)]]*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

## zenml.zen_stores.schemas.artifact_visualization_schemas module

SQLModel implementation of artifact visualization table.

### *class* zenml.zen_stores.schemas.artifact_visualization_schemas.ArtifactVisualizationSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, type: str, uri: str, artifact_version_id: UUID)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

SQL Model for visualizations of artifacts.

#### artifact_version *: Mapped[[ArtifactVersionSchema](#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema)]*

#### artifact_version_id *: UUID*

#### created *: datetime*

#### *classmethod* from_model(artifact_visualization_request: [ArtifactVisualizationRequest](zenml.models.v2.core.md#zenml.models.v2.core.artifact_visualization.ArtifactVisualizationRequest), artifact_version_id: UUID) → [ArtifactVisualizationSchema](#zenml.zen_stores.schemas.artifact_visualization_schemas.ArtifactVisualizationSchema)

Convert a ArtifactVisualizationRequest to a ArtifactVisualizationSchema.

Args:
: artifact_visualization_request: The visualization.
  artifact_version_id: The UUID of the artifact version.

Returns:
: The ArtifactVisualizationSchema.

#### id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact_version_id': FieldInfo(annotation=UUID, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'type': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'uri': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [ArtifactVisualizationResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact_visualization.ArtifactVisualizationResponse)

Convert an ArtifactVisualizationSchema to a Visualization.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The Visualization.

#### type *: str*

#### updated *: datetime*

#### uri *: str*

## zenml.zen_stores.schemas.base_schemas module

Base classes for SQLModel schemas.

### *class* zenml.zen_stores.schemas.base_schemas.BaseSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None)

Bases: `SQLModel`

Base SQL Model for ZenML entities.

#### created *: datetime*

#### id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'registry': PydanticUndefined}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → Any

In case the Schema has a corresponding Model, this allows conversion to that model.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Raises:
: NotImplementedError: When the base class fails to implement this.

#### updated *: datetime*

### *class* zenml.zen_stores.schemas.base_schemas.NamedSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

Base Named SQL Model.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'registry': PydanticUndefined}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'name': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

## zenml.zen_stores.schemas.code_repository_schemas module

SQL Model Implementations for code repositories.

### *class* zenml.zen_stores.schemas.code_repository_schemas.CodeReferenceSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, workspace_id: UUID, code_repository_id: UUID, commit: str, subdirectory: str)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

SQL Model for code references.

#### code_repository *: Mapped[[CodeRepositorySchema](#zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema)]*

#### code_repository_id *: UUID*

#### commit *: str*

#### created *: datetime*

#### *classmethod* from_request(request: [CodeReferenceRequest](zenml.models.v2.core.md#zenml.models.v2.core.code_reference.CodeReferenceRequest), workspace_id: UUID) → [CodeReferenceSchema](#zenml.zen_stores.schemas.code_repository_schemas.CodeReferenceSchema)

Convert a CodeReferenceRequest to a CodeReferenceSchema.

Args:
: request: The request model to convert.
  workspace_id: The workspace ID.

Returns:
: The converted schema.

#### id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'code_repository_id': FieldInfo(annotation=UUID, required=True), 'commit': FieldInfo(annotation=str, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'subdirectory': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### subdirectory *: str*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [CodeReferenceResponse](zenml.models.v2.core.md#zenml.models.v2.core.code_reference.CodeReferenceResponse)

Convert a CodeReferenceSchema to a CodeReferenceResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic
  <br/>
  kwargs: Additional keyword arguments.

Returns:
: The converted model.

#### updated *: datetime*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

### *class* zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, workspace_id: UUID, user_id: UUID | None, config: str, source: str, logo_url: str | None, description: str | None)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for code repositories.

#### config *: str*

#### created *: datetime*

#### description *: str | None*

#### *classmethod* from_request(request: [CodeRepositoryRequest](zenml.models.v2.core.md#zenml.models.v2.core.code_repository.CodeRepositoryRequest)) → [CodeRepositorySchema](#zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema)

Convert a CodeRepositoryRequest to a CodeRepositorySchema.

Args:
: request: The request model to convert.

Returns:
: The converted schema.

#### id *: UUID*

#### logo_url *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config': FieldInfo(annotation=str, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'description': FieldInfo(annotation=Union[str, NoneType], required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'logo_url': FieldInfo(annotation=Union[str, NoneType], required=True), 'name': FieldInfo(annotation=str, required=True), 'source': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### source *: str*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [CodeRepositoryResponse](zenml.models.v2.core.md#zenml.models.v2.core.code_repository.CodeRepositoryResponse)

Convert a CodeRepositorySchema to a CodeRepositoryResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created CodeRepositoryResponse.

#### update(update: [CodeRepositoryUpdate](zenml.models.v2.core.md#zenml.models.v2.core.code_repository.CodeRepositoryUpdate)) → [CodeRepositorySchema](#zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema)

Update a CodeRepositorySchema with a CodeRepositoryUpdate.

Args:
: update: The update model.

Returns:
: The updated CodeRepositorySchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

## zenml.zen_stores.schemas.component_schemas module

SQL Model Implementations for Stack Components.

### *class* zenml.zen_stores.schemas.component_schemas.StackComponentSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, type: str, flavor: str, configuration: bytes, labels: bytes | None, component_spec_path: str | None, workspace_id: UUID, user_id: UUID | None, connector_id: UUID | None, connector_resource_id: str | None)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for stack components.

#### component_spec_path *: str | None*

#### configuration *: bytes*

#### connector *: Mapped[[ServiceConnectorSchema](#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema) | None]*

#### connector_id *: UUID | None*

#### connector_resource_id *: str | None*

#### created *: datetime*

#### flavor *: str*

#### flavor_schema *: Mapped[[FlavorSchema](#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema) | None]*

#### id *: UUID*

#### labels *: bytes | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'component_spec_path': FieldInfo(annotation=Union[str, NoneType], required=True), 'configuration': FieldInfo(annotation=bytes, required=True), 'connector_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'connector_resource_id': FieldInfo(annotation=Union[str, NoneType], required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'flavor': FieldInfo(annotation=str, required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'labels': FieldInfo(annotation=Union[bytes, NoneType], required=True), 'name': FieldInfo(annotation=str, required=True), 'type': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### run_metadata *: Mapped[List[[RunMetadataSchema](#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema)]]*

#### run_or_step_logs *: Mapped[List[[LogsSchema](#zenml.zen_stores.schemas.logs_schemas.LogsSchema)]]*

#### schedules *: Mapped[List[[ScheduleSchema](#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema)]]*

#### stacks *: Mapped[List[[StackSchema](#zenml.zen_stores.schemas.stack_schemas.StackSchema)]]*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [ComponentResponse](zenml.models.v2.core.md#zenml.models.v2.core.component.ComponentResponse)

Creates a ComponentModel from an instance of a StackComponentSchema.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: A ComponentModel

#### type *: str*

#### update(component_update: [ComponentUpdate](zenml.models.v2.core.md#zenml.models.v2.core.component.ComponentUpdate)) → [StackComponentSchema](#zenml.zen_stores.schemas.component_schemas.StackComponentSchema)

Updates a StackComponentSchema from a ComponentUpdate.

Args:
: component_update: The ComponentUpdate to update from.

Returns:
: The updated StackComponentSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

## zenml.zen_stores.schemas.constants module

Constant values needed by schema objects.

## zenml.zen_stores.schemas.device_schemas module

SQLModel implementation for authorized OAuth2 devices.

### *class* zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, client_id: UUID, user_code: str, device_code: str, status: str, failed_auth_attempts: int = 0, expires: datetime | None = None, last_login: datetime | None = None, trusted_device: bool = False, os: str | None = None, ip_address: str | None = None, hostname: str | None = None, python_version: str | None = None, zenml_version: str | None = None, city: str | None = None, region: str | None = None, country: str | None = None, user_id: UUID | None)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

SQL Model for authorized OAuth2 devices.

#### city *: str | None*

#### client_id *: UUID*

#### country *: str | None*

#### created *: datetime*

#### device_code *: str*

#### expires *: datetime | None*

#### failed_auth_attempts *: int*

#### *classmethod* from_request(request: [OAuthDeviceInternalRequest](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceInternalRequest)) → Tuple[[OAuthDeviceSchema](#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema), str, str]

Create an authorized device DB entry from a device authorization request.

Args:
: request: The device authorization request.

Returns:
: The created OAuthDeviceSchema, the user code and the device code.

#### hostname *: str | None*

#### id *: UUID*

#### internal_update(device_update: [OAuthDeviceInternalUpdate](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceInternalUpdate)) → Tuple[[OAuthDeviceSchema](#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema), str | None, str | None]

Update an authorized device from an internal device update model.

Args:
: device_update: The internal device update model.

Returns:
: The updated OAuthDeviceSchema and the new user code and device
  code, if they were generated.

#### ip_address *: str | None*

#### last_login *: datetime | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'city': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'client_id': FieldInfo(annotation=UUID, required=True), 'country': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'device_code': FieldInfo(annotation=str, required=True), 'expires': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'failed_auth_attempts': FieldInfo(annotation=int, required=False, default=0), 'hostname': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'ip_address': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'last_login': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'os': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'python_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'region': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'status': FieldInfo(annotation=str, required=True), 'trusted_device': FieldInfo(annotation=bool, required=False, default=False), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_code': FieldInfo(annotation=str, required=True), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'zenml_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### os *: str | None*

#### python_version *: str | None*

#### region *: str | None*

#### status *: str*

#### to_internal_model(hydrate: bool = False) → [OAuthDeviceInternalResponse](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceInternalResponse)

Convert a device schema to an internal device response model.

Args:
: hydrate: bool to decide whether to return a hydrated version of the
  : model.

Returns:
: The converted internal device response model.

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [OAuthDeviceResponse](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceResponse)

Convert a device schema to a device response model.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The converted device response model.

#### trusted_device *: bool*

#### update(device_update: [OAuthDeviceUpdate](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceUpdate)) → [OAuthDeviceSchema](#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema)

Update an authorized device from a device update model.

Args:
: device_update: The device update model.

Returns:
: The updated OAuthDeviceSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema) | None]*

#### user_code *: str*

#### user_id *: UUID | None*

#### zenml_version *: str | None*

## zenml.zen_stores.schemas.event_source_schemas module

SQL Model Implementations for event sources.

### *class* zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, workspace_id: UUID, user_id: UUID | None, flavor: str, plugin_subtype: str, description: str, configuration: bytes, is_active: bool)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for tag.

#### configuration *: bytes*

#### created *: datetime*

#### description *: str*

#### flavor *: str*

#### *classmethod* from_request(request: [EventSourceRequest](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceRequest)) → [EventSourceSchema](#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema)

Convert an EventSourceRequest to an EventSourceSchema.

Args:
: request: The request model to convert.

Returns:
: The converted schema.

#### id *: UUID*

#### is_active *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'configuration': FieldInfo(annotation=bytes, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'description': FieldInfo(annotation=str, required=True), 'flavor': FieldInfo(annotation=str, required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'is_active': FieldInfo(annotation=bool, required=True), 'name': FieldInfo(annotation=str, required=True), 'plugin_subtype': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### plugin_subtype *: str*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [EventSourceResponse](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceResponse)

Convert an EventSourceSchema to an EventSourceResponse.

Args:
: include_metadata: Flag deciding whether to include the output model(s)
  : metadata fields in the response.
  <br/>
  include_resources: Flag deciding whether to include the output model(s)
  : metadata fields in the response.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created EventSourceResponse.

#### triggers *: Mapped[List[[TriggerSchema](#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema)]]*

#### update(update: [EventSourceUpdate](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceUpdate)) → [EventSourceSchema](#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema)

Updates a EventSourceSchema from a EventSourceUpdate.

Args:
: update: The EventSourceUpdate to update from.

Returns:
: The updated EventSourceSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

## zenml.zen_stores.schemas.flavor_schemas module

SQL Model Implementations for Flavors.

### *class* zenml.zen_stores.schemas.flavor_schemas.FlavorSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, type: str, source: str, config_schema: str, integration: str | None = '', connector_type: str | None, connector_resource_type: str | None, connector_resource_id_attr: str | None, workspace_id: UUID | None, user_id: UUID | None, logo_url: str | None, docs_url: str | None, sdk_docs_url: str | None, is_custom: bool = True)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for flavors.

Attributes:
: type: The type of the flavor.
  source: The source of the flavor.
  config_schema: The config schema of the flavor.
  integration: The integration associated with the flavor.

#### config_schema *: str*

#### connector_resource_id_attr *: str | None*

#### connector_resource_type *: str | None*

#### connector_type *: str | None*

#### created *: datetime*

#### docs_url *: str | None*

#### id *: UUID*

#### integration *: str | None*

#### is_custom *: bool*

#### logo_url *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config_schema': FieldInfo(annotation=str, required=True), 'connector_resource_id_attr': FieldInfo(annotation=Union[str, NoneType], required=True), 'connector_resource_type': FieldInfo(annotation=Union[str, NoneType], required=True), 'connector_type': FieldInfo(annotation=Union[str, NoneType], required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'docs_url': FieldInfo(annotation=Union[str, NoneType], required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'integration': FieldInfo(annotation=Union[str, NoneType], required=False, default=''), 'is_custom': FieldInfo(annotation=bool, required=False, default=True), 'logo_url': FieldInfo(annotation=Union[str, NoneType], required=True), 'name': FieldInfo(annotation=str, required=True), 'sdk_docs_url': FieldInfo(annotation=Union[str, NoneType], required=True), 'source': FieldInfo(annotation=str, required=True), 'type': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=Union[UUID, NoneType], required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### sdk_docs_url *: str | None*

#### source *: str*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [FlavorResponse](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorResponse)

Converts a flavor schema to a flavor model.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The flavor model.

#### type *: str*

#### update(flavor_update: [FlavorUpdate](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorUpdate)) → [FlavorSchema](#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema)

Update a FlavorSchema from a FlavorUpdate.

Args:
: flavor_update: The FlavorUpdate from which to update the schema.

Returns:
: The updated FlavorSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema) | None]*

#### workspace_id *: UUID | None*

## zenml.zen_stores.schemas.logs_schemas module

SQLModel implementation of pipeline logs tables.

### *class* zenml.zen_stores.schemas.logs_schemas.LogsSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, uri: str, pipeline_run_id: UUID | None, step_run_id: UUID | None, artifact_store_id: UUID)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

SQL Model for logs.

#### artifact_store *: Mapped[[StackComponentSchema](#zenml.zen_stores.schemas.component_schemas.StackComponentSchema) | None]*

#### artifact_store_id *: UUID*

#### created *: datetime*

#### id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact_store_id': FieldInfo(annotation=UUID, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'pipeline_run_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'step_run_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'uri': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### pipeline_run *: Mapped[[PipelineRunSchema](#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema) | None]*

#### pipeline_run_id *: UUID | None*

#### step_run *: Mapped[[StepRunSchema](#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema) | None]*

#### step_run_id *: UUID | None*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [LogsResponse](zenml.models.v2.core.md#zenml.models.v2.core.logs.LogsResponse)

Convert a LogsSchema to a LogsResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created LogsResponse.

#### updated *: datetime*

#### uri *: str*

## zenml.zen_stores.schemas.model_schemas module

SQLModel implementation of model tables.

### *class* zenml.zen_stores.schemas.model_schemas.ModelSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, workspace_id: UUID, user_id: UUID | None, license: str, description: str, audience: str, use_cases: str, limitations: str, trade_offs: str, ethics: str, save_models_to_registry: bool)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for model.

#### artifact_links *: Mapped[List[[ModelVersionArtifactSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema)]]*

#### audience *: str*

#### created *: datetime*

#### description *: str*

#### ethics *: str*

#### *classmethod* from_request(model_request: [ModelRequest](zenml.models.v2.core.md#zenml.models.v2.core.model.ModelRequest)) → [ModelSchema](#zenml.zen_stores.schemas.model_schemas.ModelSchema)

Convert an ModelRequest to an ModelSchema.

Args:
: model_request: The request model to convert.

Returns:
: The converted schema.

#### id *: UUID*

#### license *: str*

#### limitations *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'audience': FieldInfo(annotation=str, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'description': FieldInfo(annotation=str, required=True), 'ethics': FieldInfo(annotation=str, required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'license': FieldInfo(annotation=str, required=True), 'limitations': FieldInfo(annotation=str, required=True), 'name': FieldInfo(annotation=str, required=True), 'save_models_to_registry': FieldInfo(annotation=bool, required=True), 'trade_offs': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'use_cases': FieldInfo(annotation=str, required=True), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_versions *: Mapped[List[[ModelVersionSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema)]]*

#### name *: str*

#### pipeline_run_links *: Mapped[List[[ModelVersionPipelineRunSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema)]]*

#### save_models_to_registry *: bool*

#### tags *: Mapped[List[[TagResourceSchema](#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema)]]*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [ModelResponse](zenml.models.v2.core.md#zenml.models.v2.core.model.ModelResponse)

Convert an ModelSchema to an ModelResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created ModelResponse.

#### trade_offs *: str*

#### update(model_update: [ModelUpdate](zenml.models.v2.core.md#zenml.models.v2.core.model.ModelUpdate)) → [ModelSchema](#zenml.zen_stores.schemas.model_schemas.ModelSchema)

Updates a ModelSchema from a ModelUpdate.

Args:
: model_update: The ModelUpdate to update from.

Returns:
: The updated ModelSchema.

#### updated *: datetime*

#### use_cases *: str*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

### *class* zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, workspace_id: UUID, user_id: UUID | None, model_id: UUID, model_version_id: UUID, artifact_version_id: UUID, is_model_artifact: bool, is_deployment_artifact: bool)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

SQL Model for linking of Model Versions and Artifacts M:M.

#### artifact_version *: Mapped[[ArtifactVersionSchema](#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema)]*

#### artifact_version_id *: UUID*

#### created *: datetime*

#### *classmethod* from_request(model_version_artifact_request: [ModelVersionArtifactRequest](zenml.models.v2.core.md#zenml.models.v2.core.model_version_artifact.ModelVersionArtifactRequest)) → [ModelVersionArtifactSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema)

Convert an ModelVersionArtifactRequest to a ModelVersionArtifactSchema.

Args:
: model_version_artifact_request: The request link to convert.

Returns:
: The converted schema.

#### id *: UUID*

#### is_deployment_artifact *: bool*

#### is_model_artifact *: bool*

#### model *: Mapped[[ModelSchema](#zenml.zen_stores.schemas.model_schemas.ModelSchema)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'protected_namespaces': (), 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact_version_id': FieldInfo(annotation=UUID, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'is_deployment_artifact': FieldInfo(annotation=bool, required=True), 'is_model_artifact': FieldInfo(annotation=bool, required=True), 'model_id': FieldInfo(annotation=UUID, required=True), 'model_version_id': FieldInfo(annotation=UUID, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_id *: UUID*

#### model_version *: Mapped[[ModelVersionSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema)]*

#### model_version_id *: UUID*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [ModelVersionArtifactResponse](zenml.models.v2.core.md#zenml.models.v2.core.model_version_artifact.ModelVersionArtifactResponse)

Convert an ModelVersionArtifactSchema to an ModelVersionArtifactResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created ModelVersionArtifactResponseModel.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

### *class* zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, workspace_id: UUID, user_id: UUID | None, model_id: UUID, model_version_id: UUID, pipeline_run_id: UUID)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

SQL Model for linking of Model Versions and Pipeline Runs M:M.

#### created *: datetime*

#### *classmethod* from_request(model_version_pipeline_run_request: [ModelVersionPipelineRunRequest](zenml.models.v2.core.md#zenml.models.v2.core.model_version_pipeline_run.ModelVersionPipelineRunRequest)) → [ModelVersionPipelineRunSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema)

Convert an ModelVersionPipelineRunRequest to an ModelVersionPipelineRunSchema.

Args:
: model_version_pipeline_run_request: The request link to convert.

Returns:
: The converted schema.

#### id *: UUID*

#### model *: Mapped[[ModelSchema](#zenml.zen_stores.schemas.model_schemas.ModelSchema)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'protected_namespaces': (), 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'model_id': FieldInfo(annotation=UUID, required=True), 'model_version_id': FieldInfo(annotation=UUID, required=True), 'pipeline_run_id': FieldInfo(annotation=UUID, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_id *: UUID*

#### model_version *: Mapped[[ModelVersionSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema)]*

#### model_version_id *: UUID*

#### pipeline_run *: Mapped[[PipelineRunSchema](#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema)]*

#### pipeline_run_id *: UUID*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [ModelVersionPipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.model_version_pipeline_run.ModelVersionPipelineRunResponse)

Convert an ModelVersionPipelineRunSchema to an ModelVersionPipelineRunResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created ModelVersionPipelineRunResponse.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

### *class* zenml.zen_stores.schemas.model_schemas.ModelVersionSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, workspace_id: UUID, user_id: UUID | None, model_id: UUID, number: int, description: str, stage: str)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for model version.

#### artifact_links *: Mapped[List[[ModelVersionArtifactSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema)]]*

#### created *: datetime*

#### description *: str*

#### *classmethod* from_request(model_version_request: [ModelVersionRequest](zenml.models.v2.core.md#zenml.models.v2.core.model_version.ModelVersionRequest)) → [ModelVersionSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema)

Convert an ModelVersionRequest to an ModelVersionSchema.

Args:
: model_version_request: The request model version to convert.

Returns:
: The converted schema.

#### id *: UUID*

#### model *: Mapped[[ModelSchema](#zenml.zen_stores.schemas.model_schemas.ModelSchema)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'protected_namespaces': (), 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'description': FieldInfo(annotation=str, required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'model_id': FieldInfo(annotation=UUID, required=True), 'name': FieldInfo(annotation=str, required=True), 'number': FieldInfo(annotation=int, required=True), 'stage': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_id *: UUID*

#### name *: str*

#### number *: int*

#### pipeline_run_links *: Mapped[List[[ModelVersionPipelineRunSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema)]]*

#### pipeline_runs *: Mapped[List[[PipelineRunSchema](#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema)]]*

#### run_metadata *: Mapped[List[[RunMetadataSchema](#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema)]]*

#### services *: Mapped[List[[ServiceSchema](#zenml.zen_stores.schemas.service_schemas.ServiceSchema)]]*

#### stage *: str*

#### step_runs *: Mapped[List[[StepRunSchema](#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema)]]*

#### tags *: Mapped[List[[TagResourceSchema](#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema)]]*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [ModelVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.model_version.ModelVersionResponse)

Convert an ModelVersionSchema to an ModelVersionResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created ModelVersionResponse.

#### update(target_stage: str | None = None, target_name: str | None = None, target_description: str | None = None) → [ModelVersionSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema)

Updates a ModelVersionSchema to a target stage.

Args:
: target_stage: The stage to be updated.
  target_name: The version name to be updated.
  target_description: The version description to be updated.

Returns:
: The updated ModelVersionSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

## zenml.zen_stores.schemas.pipeline_build_schemas module

SQLModel implementation of pipeline build tables.

### *class* zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, user_id: UUID | None, workspace_id: UUID, stack_id: UUID | None, pipeline_id: UUID | None, images: str, is_local: bool, contains_code: bool, zenml_version: str | None, python_version: str | None, checksum: str | None, stack_checksum: str | None)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

SQL Model for pipeline builds.

#### checksum *: str | None*

#### contains_code *: bool*

#### created *: datetime*

#### *classmethod* from_request(request: [PipelineBuildRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_build.PipelineBuildRequest)) → [PipelineBuildSchema](#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema)

Convert a PipelineBuildRequest to a PipelineBuildSchema.

Args:
: request: The request to convert.

Returns:
: The created PipelineBuildSchema.

#### id *: UUID*

#### images *: str*

#### is_local *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'checksum': FieldInfo(annotation=Union[str, NoneType], required=True), 'contains_code': FieldInfo(annotation=bool, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'images': FieldInfo(annotation=str, required=True), 'is_local': FieldInfo(annotation=bool, required=True), 'pipeline_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'python_version': FieldInfo(annotation=Union[str, NoneType], required=True), 'stack_checksum': FieldInfo(annotation=Union[str, NoneType], required=True), 'stack_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True), 'zenml_version': FieldInfo(annotation=Union[str, NoneType], required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### pipeline *: Mapped[[PipelineSchema](#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema) | None]*

#### pipeline_id *: UUID | None*

#### python_version *: str | None*

#### stack *: Mapped[[StackSchema](#zenml.zen_stores.schemas.stack_schemas.StackSchema) | None]*

#### stack_checksum *: str | None*

#### stack_id *: UUID | None*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [PipelineBuildResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_build.PipelineBuildResponse)

Convert a PipelineBuildSchema to a PipelineBuildResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created PipelineBuildResponse.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

#### zenml_version *: str | None*

## zenml.zen_stores.schemas.pipeline_deployment_schemas module

SQLModel implementation of pipeline deployment tables.

### *class* zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, pipeline_configuration: str, step_configurations: str, client_environment: str, run_name_template: str, client_version: str, server_version: str, pipeline_version_hash: str | None = None, pipeline_spec: str | None, code_path: str | None, user_id: UUID | None, workspace_id: UUID, stack_id: UUID | None, pipeline_id: UUID | None, schedule_id: UUID | None, build_id: UUID | None, code_reference_id: UUID | None, template_id: UUID | None = None)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

SQL Model for pipeline deployments.

#### build *: Mapped[[PipelineBuildSchema](#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema) | None]*

#### build_id *: UUID | None*

#### client_environment *: str*

#### client_version *: str*

#### code_path *: str | None*

#### code_reference *: Mapped[[CodeReferenceSchema](#zenml.zen_stores.schemas.code_repository_schemas.CodeReferenceSchema) | None]*

#### code_reference_id *: UUID | None*

#### created *: datetime*

#### *classmethod* from_request(request: [PipelineDeploymentRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentRequest), code_reference_id: UUID | None) → [PipelineDeploymentSchema](#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema)

Convert a PipelineDeploymentRequest to a PipelineDeploymentSchema.

Args:
: request: The request to convert.
  code_reference_id: Optional ID of the code reference for the
  <br/>
  > deployment.

Returns:
: The created PipelineDeploymentSchema.

#### id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'build_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'client_environment': FieldInfo(annotation=str, required=True), 'client_version': FieldInfo(annotation=str, required=True), 'code_path': FieldInfo(annotation=Union[str, NoneType], required=True), 'code_reference_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'pipeline_configuration': FieldInfo(annotation=str, required=True), 'pipeline_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'pipeline_spec': FieldInfo(annotation=Union[str, NoneType], required=True), 'pipeline_version_hash': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'run_name_template': FieldInfo(annotation=str, required=True), 'schedule_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'server_version': FieldInfo(annotation=str, required=True), 'stack_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'step_configurations': FieldInfo(annotation=str, required=True), 'template_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### pipeline *: Mapped[[PipelineSchema](#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema) | None]*

#### pipeline_configuration *: str*

#### pipeline_id *: UUID | None*

#### pipeline_runs *: Mapped[List[[PipelineRunSchema](#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema)]]*

#### pipeline_spec *: str | None*

#### pipeline_version_hash *: str | None*

#### run_name_template *: str*

#### schedule *: Mapped[[ScheduleSchema](#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema) | None]*

#### schedule_id *: UUID | None*

#### server_version *: str*

#### stack *: Mapped[[StackSchema](#zenml.zen_stores.schemas.stack_schemas.StackSchema) | None]*

#### stack_id *: UUID | None*

#### step_configurations *: str*

#### step_runs *: Mapped[List[[StepRunSchema](#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema)]]*

#### template_id *: UUID | None*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [PipelineDeploymentResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentResponse)

Convert a PipelineDeploymentSchema to a PipelineDeploymentResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created PipelineDeploymentResponse.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

## zenml.zen_stores.schemas.pipeline_run_schemas module

SQLModel implementation of pipeline run tables.

### *class* zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, orchestrator_run_id: str | None, start_time: datetime | None, end_time: datetime | None = None, status: str, orchestrator_environment: str | None, deployment_id: UUID | None, user_id: UUID | None, workspace_id: UUID, pipeline_id: UUID | None, model_version_id: UUID, pipeline_configuration: str | None, client_environment: str | None, stack_id: UUID | None, build_id: UUID | None, schedule_id: UUID | None, trigger_execution_id: UUID | None)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for pipeline runs.

#### build *: Mapped[[PipelineBuildSchema](#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema) | None]*

#### build_id *: UUID | None*

#### client_environment *: str | None*

#### created *: datetime*

#### deployment *: Mapped[[PipelineDeploymentSchema](#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema) | None]*

#### deployment_id *: UUID | None*

#### end_time *: datetime | None*

#### *classmethod* from_request(request: [PipelineRunRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunRequest)) → [PipelineRunSchema](#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema)

Convert a PipelineRunRequest to a PipelineRunSchema.

Args:
: request: The request to convert.

Returns:
: The created PipelineRunSchema.

#### id *: UUID*

#### logs *: Mapped[[LogsSchema](#zenml.zen_stores.schemas.logs_schemas.LogsSchema) | None]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'protected_namespaces': (), 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'build_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'client_environment': FieldInfo(annotation=Union[str, NoneType], required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'deployment_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'end_time': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'model_version_id': FieldInfo(annotation=UUID, required=True), 'name': FieldInfo(annotation=str, required=True), 'orchestrator_environment': FieldInfo(annotation=Union[str, NoneType], required=True), 'orchestrator_run_id': FieldInfo(annotation=Union[str, NoneType], required=True), 'pipeline_configuration': FieldInfo(annotation=Union[str, NoneType], required=True), 'pipeline_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'schedule_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'stack_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'start_time': FieldInfo(annotation=Union[datetime, NoneType], required=True), 'status': FieldInfo(annotation=str, required=True), 'trigger_execution_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_version *: Mapped[[ModelVersionSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema)]*

#### model_version_id *: UUID*

#### model_versions_pipeline_runs_links *: Mapped[List[[ModelVersionPipelineRunSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema)]]*

#### name *: str*

#### orchestrator_environment *: str | None*

#### orchestrator_run_id *: str | None*

#### pipeline *: Mapped[[PipelineSchema](#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema) | None]*

#### pipeline_configuration *: str | None*

#### pipeline_id *: UUID | None*

#### run_metadata *: Mapped[List[[RunMetadataSchema](#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema)]]*

#### schedule *: Mapped[[ScheduleSchema](#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema) | None]*

#### schedule_id *: UUID | None*

#### services *: Mapped[List[[ServiceSchema](#zenml.zen_stores.schemas.service_schemas.ServiceSchema)]]*

#### stack *: Mapped[[StackSchema](#zenml.zen_stores.schemas.stack_schemas.StackSchema) | None]*

#### stack_id *: UUID | None*

#### start_time *: datetime | None*

#### status *: str*

#### step_runs *: Mapped[List[[StepRunSchema](#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema)]]*

#### tags *: Mapped[List[[TagResourceSchema](#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema)]]*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse)

Convert a PipelineRunSchema to a PipelineRunResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created PipelineRunResponse.

Raises:
: RuntimeError: if the model creation fails.

#### trigger_execution *: Mapped[[TriggerExecutionSchema](#zenml.zen_stores.schemas.trigger_schemas.TriggerExecutionSchema) | None]*

#### trigger_execution_id *: UUID | None*

#### update(run_update: [PipelineRunUpdate](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunUpdate)) → [PipelineRunSchema](#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema)

Update a PipelineRunSchema with a PipelineRunUpdate.

Args:
: run_update: The PipelineRunUpdate to update with.

Returns:
: The updated PipelineRunSchema.

#### update_placeholder(request: [PipelineRunRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunRequest)) → [PipelineRunSchema](#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema)

Update a placeholder run.

Args:
: request: The pipeline run request which should replace the
  : placeholder.

Raises:
: RuntimeError: If the DB entry does not represent a placeholder run.
  ValueError: If the run request does not match the deployment or
  <br/>
  > pipeline ID of the placeholder run.

Returns:
: The updated PipelineRunSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

## zenml.zen_stores.schemas.pipeline_schemas module

SQL Model Implementations for Pipelines and Pipeline Runs.

### *class* zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, description: str | None, workspace_id: UUID, user_id: UUID | None)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for pipelines.

#### builds *: Mapped[List[[PipelineBuildSchema](#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema)]]*

#### created *: datetime*

#### deployments *: Mapped[List[[PipelineDeploymentSchema](#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema)]]*

#### description *: str | None*

#### *classmethod* from_request(pipeline_request: [PipelineRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineRequest)) → [PipelineSchema](#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema)

Convert a PipelineRequest to a PipelineSchema.

Args:
: pipeline_request: The request model to convert.

Returns:
: The converted schema.

#### id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'description': FieldInfo(annotation=Union[str, NoneType], required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'name': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### runs *: Mapped[List[[PipelineRunSchema](#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema)]]*

#### schedules *: Mapped[List[[ScheduleSchema](#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema)]]*

#### tags *: Mapped[List[[TagResourceSchema](#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema)]]*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [PipelineResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineResponse)

Convert a PipelineSchema to a PipelineResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created PipelineResponse.

#### update(pipeline_update: [PipelineUpdate](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineUpdate)) → [PipelineSchema](#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema)

Update a PipelineSchema with a PipelineUpdate.

Args:
: pipeline_update: The update model.

Returns:
: The updated PipelineSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

## zenml.zen_stores.schemas.run_metadata_schemas module

SQLModel implementation of pipeline run metadata tables.

### *class* zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, resource_id: UUID, resource_type: str, stack_component_id: UUID | None, user_id: UUID | None, workspace_id: UUID, key: str, value: str, type: str)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

SQL Model for run metadata.

#### artifact_version *: Mapped[List[[ArtifactVersionSchema](#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema)]]*

#### created *: datetime*

#### id *: UUID*

#### key *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'key': FieldInfo(annotation=str, required=True), 'resource_id': FieldInfo(annotation=UUID, required=True), 'resource_type': FieldInfo(annotation=str, required=True), 'stack_component_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'type': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'value': FieldInfo(annotation=str, required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_version *: Mapped[List[[ModelVersionSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema)]]*

#### pipeline_run *: Mapped[List[[PipelineRunSchema](#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema)]]*

#### resource_id *: UUID*

#### resource_type *: str*

#### stack_component *: Mapped[[StackComponentSchema](#zenml.zen_stores.schemas.component_schemas.StackComponentSchema) | None]*

#### stack_component_id *: UUID | None*

#### step_run *: Mapped[List[[StepRunSchema](#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema)]]*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [RunMetadataResponse](zenml.models.v2.core.md#zenml.models.v2.core.run_metadata.RunMetadataResponse)

Convert a RunMetadataSchema to a RunMetadataResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created RunMetadataResponse.

#### type *: str*

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### value *: str*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

## zenml.zen_stores.schemas.run_template_schemas module

SQLModel implementation of run template tables.

### *class* zenml.zen_stores.schemas.run_template_schemas.RunTemplateSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, description: str | None, user_id: UUID | None, workspace_id: UUID, source_deployment_id: UUID | None)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

SQL Model for run templates.

#### created *: datetime*

#### description *: str | None*

#### *classmethod* from_request(request: [RunTemplateRequest](zenml.models.v2.core.md#zenml.models.v2.core.run_template.RunTemplateRequest)) → [RunTemplateSchema](#zenml.zen_stores.schemas.run_template_schemas.RunTemplateSchema)

Create a schema from a request.

Args:
: request: The request to convert.

Returns:
: The created schema.

#### id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'description': FieldInfo(annotation=Union[str, NoneType], required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'name': FieldInfo(annotation=str, required=True), 'source_deployment_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### runs *: Mapped[List[[PipelineRunSchema](#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema)]]*

#### source_deployment *: Mapped[[PipelineDeploymentSchema](#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema) | None]*

#### source_deployment_id *: UUID | None*

#### tags *: Mapped[List[[TagResourceSchema](#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema)]]*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [RunTemplateResponse](zenml.models.v2.core.md#zenml.models.v2.core.run_template.RunTemplateResponse)

Convert the schema to a response model.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: Model representing this schema.

#### update(update: [RunTemplateUpdate](zenml.models.v2.core.md#zenml.models.v2.core.run_template.RunTemplateUpdate)) → [RunTemplateSchema](#zenml.zen_stores.schemas.run_template_schemas.RunTemplateSchema)

Update the schema.

Args:
: update: The update model.

Returns:
: The updated schema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

## zenml.zen_stores.schemas.schedule_schema module

SQL Model Implementations for Pipeline Schedules.

### *class* zenml.zen_stores.schemas.schedule_schema.ScheduleSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, workspace_id: UUID, user_id: UUID | None, pipeline_id: UUID | None, orchestrator_id: UUID | None, active: bool, cron_expression: str | None, start_time: datetime | None, end_time: datetime | None, interval_second: float | None, catchup: bool, run_once_start_time: datetime | None)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for schedules.

#### active *: bool*

#### catchup *: bool*

#### created *: datetime*

#### cron_expression *: str | None*

#### deployment *: Mapped[[PipelineDeploymentSchema](#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema) | None]*

#### end_time *: datetime | None*

#### *classmethod* from_request(schedule_request: [ScheduleRequest](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleRequest)) → [ScheduleSchema](#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema)

Create a ScheduleSchema from a ScheduleRequest.

Args:
: schedule_request: The ScheduleRequest to create the schema from.

Returns:
: The created ScheduleSchema.

#### id *: UUID*

#### interval_second *: float | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'active': FieldInfo(annotation=bool, required=True), 'catchup': FieldInfo(annotation=bool, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'cron_expression': FieldInfo(annotation=Union[str, NoneType], required=True), 'end_time': FieldInfo(annotation=Union[datetime, NoneType], required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'interval_second': FieldInfo(annotation=Union[float, NoneType], required=True), 'name': FieldInfo(annotation=str, required=True), 'orchestrator_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'pipeline_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'run_once_start_time': FieldInfo(annotation=Union[datetime, NoneType], required=True), 'start_time': FieldInfo(annotation=Union[datetime, NoneType], required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### orchestrator *: Mapped[[StackComponentSchema](#zenml.zen_stores.schemas.component_schemas.StackComponentSchema)]*

#### orchestrator_id *: UUID | None*

#### pipeline *: Mapped[[PipelineSchema](#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema)]*

#### pipeline_id *: UUID | None*

#### run_once_start_time *: datetime | None*

#### start_time *: datetime | None*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [ScheduleResponse](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleResponse)

Convert a ScheduleSchema to a ScheduleResponseModel.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created ScheduleResponseModel.

#### update(schedule_update: [ScheduleUpdate](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleUpdate)) → [ScheduleSchema](#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema)

Update a ScheduleSchema from a ScheduleUpdateModel.

Args:
: schedule_update: The ScheduleUpdateModel to update the schema from.

Returns:
: The updated ScheduleSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

## zenml.zen_stores.schemas.schema_utils module

Utility functions for SQLModel schemas.

### zenml.zen_stores.schemas.schema_utils.build_foreign_key_field(source: str, target: str, source_column: str, target_column: str, ondelete: str, nullable: bool, \*\*sa_column_kwargs: Any) → Any

Build a SQLModel foreign key field.

Args:
: source: Source table name.
  target: Target table name.
  source_column: Source column name.
  target_column: Target column name.
  ondelete: On delete behavior.
  nullable: Whether the field is nullable.
  <br/>
  ```
  **
  ```
  <br/>
  sa_column_kwargs: Keyword arguments for the SQLAlchemy column.

Returns:
: SQLModel foreign key field.

Raises:
: ValueError: If the ondelete and nullable arguments are not compatible.

### zenml.zen_stores.schemas.schema_utils.foreign_key_constraint_name(source: str, target: str, source_column: str) → str

Defines the name of a foreign key constraint.

For simplicity, we use the naming convention used by alembic here:
[https://alembic.sqlalchemy.org/en/latest/batch.html#dropping-unnamed-or-named-foreign-key-constraints](https://alembic.sqlalchemy.org/en/latest/batch.html#dropping-unnamed-or-named-foreign-key-constraints).

Args:
: source: Source table name.
  target: Target table name.
  source_column: Source column name.

Returns:
: Name of the foreign key constraint.

## zenml.zen_stores.schemas.secret_schemas module

SQL Model Implementations for Secrets.

### *exception* zenml.zen_stores.schemas.secret_schemas.SecretDecodeError

Bases: `Exception`

Raised when a secret cannot be decoded or decrypted.

### *class* zenml.zen_stores.schemas.secret_schemas.SecretSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, scope: str, values: bytes | None, workspace_id: UUID, user_id: UUID)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for secrets.

Attributes:
: name: The name of the secret.
  values: The values of the secret.

#### created *: datetime*

#### *classmethod* from_request(secret: [SecretRequest](zenml.models.v2.core.md#zenml.models.v2.core.secret.SecretRequest)) → [SecretSchema](#zenml.zen_stores.schemas.secret_schemas.SecretSchema)

Create a SecretSchema from a SecretRequest.

Args:
: secret: The SecretRequest from which to create the schema.

Returns:
: The created SecretSchema.

#### get_secret_values(encryption_engine: AesGcmEngine | None = None) → Dict[str, str]

Get the secret values for this secret.

This method is used by the SQL secrets store to load the secret values
from the database.

Args:
: encryption_engine: The encryption engine to use to decrypt the
  : secret values. If None, the values will be base64 decoded.

Returns:
: The secret values

Raises:
: KeyError: if no secret values for the given ID are stored in the
  : secrets store.

#### id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'name': FieldInfo(annotation=str, required=True), 'scope': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=UUID, required=True), 'values': FieldInfo(annotation=Union[bytes, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### scope *: str*

#### set_secret_values(secret_values: Dict[str, str], encryption_engine: AesGcmEngine | None = None) → None

Create a SecretSchema from a SecretRequest.

This method is used by the SQL secrets store to store the secret values
in the database.

Args:
: secret_values: The new secret values.
  encryption_engine: The encryption engine to use to encrypt the
  <br/>
  > secret values. If None, the values will be base64 encoded.

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [SecretResponse](zenml.models.v2.core.md#zenml.models.v2.core.secret.SecretResponse)

Converts a secret schema to a secret model.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The secret model.

#### update(secret_update: [SecretUpdate](zenml.models.v2.core.md#zenml.models.v2.core.secret.SecretUpdate)) → [SecretSchema](#zenml.zen_stores.schemas.secret_schemas.SecretSchema)

Update a SecretSchema from a SecretUpdate.

Args:
: secret_update: The SecretUpdate from which to update the schema.

Returns:
: The updated SecretSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema)]*

#### user_id *: UUID*

#### values *: bytes | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

## zenml.zen_stores.schemas.server_settings_schemas module

SQLModel implementation for the server settings table.

### *class* zenml.zen_stores.schemas.server_settings_schemas.ServerSettingsSchema(\*, id: UUID, server_name: str, logo_url: str | None, active: bool = False, enable_analytics: bool = False, display_announcements: bool | None, display_updates: bool | None, onboarding_state: str | None, last_user_activity: datetime = None, updated: datetime = None)

Bases: `SQLModel`

SQL Model for the server settings.

#### active *: bool*

#### display_announcements *: bool | None*

#### display_updates *: bool | None*

#### enable_analytics *: bool*

#### id *: UUID*

#### last_user_activity *: datetime*

#### logo_url *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'active': FieldInfo(annotation=bool, required=False, default=False), 'display_announcements': FieldInfo(annotation=Union[bool, NoneType], required=True), 'display_updates': FieldInfo(annotation=Union[bool, NoneType], required=True), 'enable_analytics': FieldInfo(annotation=bool, required=False, default=False), 'id': FieldInfo(annotation=UUID, required=True), 'last_user_activity': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'logo_url': FieldInfo(annotation=Union[str, NoneType], required=True), 'onboarding_state': FieldInfo(annotation=Union[str, NoneType], required=True), 'server_name': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### onboarding_state *: str | None*

#### server_name *: str*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [ServerSettingsResponse](zenml.models.v2.core.md#zenml.models.v2.core.server_settings.ServerSettingsResponse)

Convert an ServerSettingsSchema to an ServerSettingsResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created SettingsResponse.

#### update(settings_update: [ServerSettingsUpdate](zenml.models.v2.core.md#zenml.models.v2.core.server_settings.ServerSettingsUpdate)) → [ServerSettingsSchema](#zenml.zen_stores.schemas.server_settings_schemas.ServerSettingsSchema)

Update a ServerSettingsSchema from a ServerSettingsUpdate.

Args:
: settings_update: The ServerSettingsUpdate from which
  : to update the schema.

Returns:
: The updated ServerSettingsSchema.

#### update_onboarding_state(completed_steps: Set[str]) → [ServerSettingsSchema](#zenml.zen_stores.schemas.server_settings_schemas.ServerSettingsSchema)

Update the onboarding state.

Args:
: completed_steps: Newly completed onboarding steps.

Returns:
: The updated schema.

#### updated *: datetime*

## zenml.zen_stores.schemas.service_connector_schemas module

SQL Model Implementations for Service Connectors.

### *class* zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, connector_type: str, description: str, auth_method: str, resource_types: bytes, resource_id: str | None, supports_instances: bool, configuration: bytes | None, secret_id: UUID | None, expires_at: datetime | None, expires_skew_tolerance: int | None, expiration_seconds: int | None, labels: bytes | None, workspace_id: UUID, user_id: UUID | None)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for service connectors.

#### auth_method *: str*

#### components *: Mapped[List[[StackComponentSchema](#zenml.zen_stores.schemas.component_schemas.StackComponentSchema)]]*

#### configuration *: bytes | None*

#### connector_type *: str*

#### created *: datetime*

#### description *: str*

#### expiration_seconds *: int | None*

#### expires_at *: datetime | None*

#### expires_skew_tolerance *: int | None*

#### *classmethod* from_request(connector_request: [ServiceConnectorRequest](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorRequest), secret_id: UUID | None = None) → [ServiceConnectorSchema](#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema)

Create a ServiceConnectorSchema from a ServiceConnectorRequest.

Args:
: connector_request: The ServiceConnectorRequest from which to
  : create the schema.
  <br/>
  secret_id: The ID of the secret to use for this connector.

Returns:
: The created ServiceConnectorSchema.

#### has_labels(labels: Dict[str, str | None]) → bool

Checks if the connector has the given labels.

Args:
: labels: The labels to check for.

Returns:
: Whether the connector has the given labels.

#### id *: UUID*

#### labels *: bytes | None*

#### *property* labels_dict *: Dict[str, str]*

Returns the labels as a dictionary.

Returns:
: The labels as a dictionary.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'auth_method': FieldInfo(annotation=str, required=True), 'configuration': FieldInfo(annotation=Union[bytes, NoneType], required=True), 'connector_type': FieldInfo(annotation=str, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'description': FieldInfo(annotation=str, required=True), 'expiration_seconds': FieldInfo(annotation=Union[int, NoneType], required=True), 'expires_at': FieldInfo(annotation=Union[datetime, NoneType], required=True), 'expires_skew_tolerance': FieldInfo(annotation=Union[int, NoneType], required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'labels': FieldInfo(annotation=Union[bytes, NoneType], required=True), 'name': FieldInfo(annotation=str, required=True), 'resource_id': FieldInfo(annotation=Union[str, NoneType], required=True), 'resource_types': FieldInfo(annotation=bytes, required=True), 'secret_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'supports_instances': FieldInfo(annotation=bool, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### resource_id *: str | None*

#### resource_types *: bytes*

#### *property* resource_types_list *: List[str]*

Returns the resource types as a list.

Returns:
: The resource types as a list.

#### secret_id *: UUID | None*

#### supports_instances *: bool*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [ServiceConnectorResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorResponse)

Creates a ServiceConnector from a ServiceConnectorSchema.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: A ServiceConnectorModel

#### update(connector_update: [ServiceConnectorUpdate](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorUpdate), secret_id: UUID | None = None) → [ServiceConnectorSchema](#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema)

Updates a ServiceConnectorSchema from a ServiceConnectorUpdate.

Args:
: connector_update: The ServiceConnectorUpdate to update from.
  secret_id: The ID of the secret to use for this connector.

Returns:
: The updated ServiceConnectorSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

## zenml.zen_stores.schemas.service_schemas module

SQLModel implementation of service table.

### *class* zenml.zen_stores.schemas.service_schemas.ServiceSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, workspace_id: UUID, user_id: UUID | None, service_source: str | None, service_type: str, type: str, flavor: str, admin_state: str | None, state: str | None, labels: bytes | None, config: bytes, status: bytes | None, endpoint: bytes | None, prediction_url: str | None, health_check_url: str | None, pipeline_name: str | None, pipeline_step_name: str | None, model_version_id: UUID | None, pipeline_run_id: UUID | None)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for service.

#### admin_state *: str | None*

#### config *: bytes*

#### created *: datetime*

#### endpoint *: bytes | None*

#### flavor *: str*

#### *classmethod* from_request(service_request: [ServiceRequest](zenml.models.v2.core.md#zenml.models.v2.core.service.ServiceRequest)) → [ServiceSchema](#zenml.zen_stores.schemas.service_schemas.ServiceSchema)

Convert a ServiceRequest to a ServiceSchema.

Args:
: service_request: The request model to convert.

Returns:
: The converted schema.

#### health_check_url *: str | None*

#### id *: UUID*

#### labels *: bytes | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'protected_namespaces': (), 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'admin_state': FieldInfo(annotation=Union[str, NoneType], required=True), 'config': FieldInfo(annotation=bytes, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'endpoint': FieldInfo(annotation=Union[bytes, NoneType], required=True), 'flavor': FieldInfo(annotation=str, required=True), 'health_check_url': FieldInfo(annotation=Union[str, NoneType], required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'labels': FieldInfo(annotation=Union[bytes, NoneType], required=True), 'model_version_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'name': FieldInfo(annotation=str, required=True), 'pipeline_name': FieldInfo(annotation=Union[str, NoneType], required=True), 'pipeline_run_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'pipeline_step_name': FieldInfo(annotation=Union[str, NoneType], required=True), 'prediction_url': FieldInfo(annotation=Union[str, NoneType], required=True), 'service_source': FieldInfo(annotation=Union[str, NoneType], required=True), 'service_type': FieldInfo(annotation=str, required=True), 'state': FieldInfo(annotation=Union[str, NoneType], required=True), 'status': FieldInfo(annotation=Union[bytes, NoneType], required=True), 'type': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_version *: Mapped[[ModelVersionSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema) | None]*

#### model_version_id *: UUID | None*

#### name *: str*

#### pipeline_name *: str | None*

#### pipeline_run *: Mapped[[PipelineRunSchema](#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema) | None]*

#### pipeline_run_id *: UUID | None*

#### pipeline_step_name *: str | None*

#### prediction_url *: str | None*

#### service_source *: str | None*

#### service_type *: str*

#### state *: str | None*

#### status *: bytes | None*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [ServiceResponse](zenml.models.v2.core.md#zenml.models.v2.core.service.ServiceResponse)

Convert an ServiceSchema to an ServiceResponse.

Args:
: include_metadata: Whether to include metadata in the response.
  include_resources: Whether to include resources in the response.
  kwargs: Additional keyword arguments.

Returns:
: The created ServiceResponse.

#### type *: str*

#### update(update: [ServiceUpdate](zenml.models.v2.core.md#zenml.models.v2.core.service.ServiceUpdate)) → [ServiceSchema](#zenml.zen_stores.schemas.service_schemas.ServiceSchema)

Updates a ServiceSchema from a ServiceUpdate.

Args:
: update: The ServiceUpdate to update from.

Returns:
: The updated ServiceSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

## zenml.zen_stores.schemas.stack_schemas module

SQL Model Implementations for Stacks.

### *class* zenml.zen_stores.schemas.stack_schemas.StackCompositionSchema(\*, stack_id: UUID, component_id: UUID)

Bases: `SQLModel`

SQL Model for stack definitions.

Join table between Stacks and StackComponents.

#### component_id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'component_id': FieldInfo(annotation=UUID, required=True), 'stack_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### stack_id *: UUID*

### *class* zenml.zen_stores.schemas.stack_schemas.StackSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, stack_spec_path: str | None, labels: bytes | None, workspace_id: UUID, user_id: UUID | None)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for stacks.

#### builds *: Mapped[List[[PipelineBuildSchema](#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema)]]*

#### components *: Mapped[List[[StackComponentSchema](#zenml.zen_stores.schemas.component_schemas.StackComponentSchema)]]*

#### created *: datetime*

#### deployments *: Mapped[List[[PipelineDeploymentSchema](#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema)]]*

#### id *: UUID*

#### labels *: bytes | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'labels': FieldInfo(annotation=Union[bytes, NoneType], required=True), 'name': FieldInfo(annotation=str, required=True), 'stack_spec_path': FieldInfo(annotation=Union[str, NoneType], required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### stack_spec_path *: str | None*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [StackResponse](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackResponse)

Converts the schema to a model.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The converted model.

#### update(stack_update: [StackUpdate](zenml.models.md#zenml.models.StackUpdate), components: List[[StackComponentSchema](#zenml.zen_stores.schemas.component_schemas.StackComponentSchema)]) → [StackSchema](#zenml.zen_stores.schemas.stack_schemas.StackSchema)

Updates a stack schema with a stack update model.

Args:
: stack_update: StackUpdate to update the stack with.
  components: List of StackComponentSchema to update the stack with.

Returns:
: The updated StackSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

## zenml.zen_stores.schemas.step_run_schemas module

SQLModel implementation of step run tables.

### *class* zenml.zen_stores.schemas.step_run_schemas.StepRunInputArtifactSchema(\*, name: str, type: str, step_id: UUID, artifact_id: UUID)

Bases: `SQLModel`

SQL Model that defines which artifacts are inputs to which step.

#### artifact_id *: UUID*

#### artifact_version *: Mapped[[ArtifactVersionSchema](#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact_id': FieldInfo(annotation=UUID, required=True), 'name': FieldInfo(annotation=str, required=True), 'step_id': FieldInfo(annotation=UUID, required=True), 'type': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### step_id *: UUID*

#### step_run *: Mapped[[StepRunSchema](#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema)]*

#### type *: str*

### *class* zenml.zen_stores.schemas.step_run_schemas.StepRunOutputArtifactSchema(\*, name: str, type: str, step_id: UUID, artifact_id: UUID)

Bases: `SQLModel`

SQL Model that defines which artifacts are outputs of which step.

#### artifact_id *: UUID*

#### artifact_version *: Mapped[[ArtifactVersionSchema](#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact_id': FieldInfo(annotation=UUID, required=True), 'name': FieldInfo(annotation=str, required=True), 'step_id': FieldInfo(annotation=UUID, required=True), 'type': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### step_id *: UUID*

#### step_run *: Mapped[[StepRunSchema](#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema)]*

#### type *: str*

### *class* zenml.zen_stores.schemas.step_run_schemas.StepRunParentsSchema(\*, parent_id: UUID, child_id: UUID)

Bases: `SQLModel`

SQL Model that defines the order of steps.

#### child_id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'child_id': FieldInfo(annotation=UUID, required=True), 'parent_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### parent_id *: UUID*

### *class* zenml.zen_stores.schemas.step_run_schemas.StepRunSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, start_time: datetime | None, end_time: datetime | None, status: str, docstring: str | None, cache_key: str | None, source_code: str | None, code_hash: str | None, step_configuration: str, original_step_run_id: UUID | None, deployment_id: UUID, pipeline_run_id: UUID, user_id: UUID | None, workspace_id: UUID, model_version_id: UUID)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for steps of pipeline runs.

#### cache_key *: str | None*

#### code_hash *: str | None*

#### created *: datetime*

#### deployment *: Mapped[[PipelineDeploymentSchema](#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema) | None]*

#### deployment_id *: UUID*

#### docstring *: str | None*

#### end_time *: datetime | None*

#### *classmethod* from_request(request: [StepRunRequest](zenml.models.v2.core.md#zenml.models.v2.core.step_run.StepRunRequest)) → [StepRunSchema](#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema)

Create a step run schema from a step run request model.

Args:
: request: The step run request model.

Returns:
: The step run schema.

#### id *: UUID*

#### input_artifacts *: Mapped[List[[StepRunInputArtifactSchema](#zenml.zen_stores.schemas.step_run_schemas.StepRunInputArtifactSchema)]]*

#### logs *: Mapped[[LogsSchema](#zenml.zen_stores.schemas.logs_schemas.LogsSchema) | None]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'protected_namespaces': (), 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'cache_key': FieldInfo(annotation=Union[str, NoneType], required=True), 'code_hash': FieldInfo(annotation=Union[str, NoneType], required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'deployment_id': FieldInfo(annotation=UUID, required=True), 'docstring': FieldInfo(annotation=Union[str, NoneType], required=True), 'end_time': FieldInfo(annotation=Union[datetime, NoneType], required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'model_version_id': FieldInfo(annotation=UUID, required=True), 'name': FieldInfo(annotation=str, required=True), 'original_step_run_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'pipeline_run_id': FieldInfo(annotation=UUID, required=True), 'source_code': FieldInfo(annotation=Union[str, NoneType], required=True), 'start_time': FieldInfo(annotation=Union[datetime, NoneType], required=True), 'status': FieldInfo(annotation=str, required=True), 'step_configuration': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_version *: Mapped[[ModelVersionSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema)]*

#### model_version_id *: UUID*

#### name *: str*

#### original_step_run_id *: UUID | None*

#### output_artifacts *: Mapped[List[[StepRunOutputArtifactSchema](#zenml.zen_stores.schemas.step_run_schemas.StepRunOutputArtifactSchema)]]*

#### parents *: Mapped[List[[StepRunParentsSchema](#zenml.zen_stores.schemas.step_run_schemas.StepRunParentsSchema)]]*

#### pipeline_run_id *: UUID*

#### run_metadata *: Mapped[List[[RunMetadataSchema](#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema)]]*

#### source_code *: str | None*

#### start_time *: datetime | None*

#### status *: str*

#### step_configuration *: str*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [StepRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.step_run.StepRunResponse)

Convert a StepRunSchema to a StepRunResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created StepRunResponse.

Raises:
: ValueError: In case the step run configuration can not be loaded.
  RuntimeError: If the step run schema does not have a deployment_id
  <br/>
  > or a step_configuration.

#### update(step_update: [StepRunUpdate](zenml.models.v2.core.md#zenml.models.v2.core.step_run.StepRunUpdate)) → [StepRunSchema](#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema)

Update a step run schema with a step run update model.

Args:
: step_update: The step run update model.

Returns:
: The updated step run schema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

## zenml.zen_stores.schemas.tag_schemas module

SQLModel implementation of tag tables.

### *class* zenml.zen_stores.schemas.tag_schemas.TagResourceSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, tag_id: UUID, resource_id: UUID, resource_type: str)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

SQL Model for tag resource relationship.

#### artifact *: Mapped[List[[ArtifactSchema](#zenml.zen_stores.schemas.artifact_schemas.ArtifactSchema)]]*

#### artifact_version *: Mapped[List[[ArtifactVersionSchema](#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema)]]*

#### created *: datetime*

#### *classmethod* from_request(request: [TagResourceRequest](zenml.models.v2.core.md#zenml.models.v2.core.tag_resource.TagResourceRequest)) → [TagResourceSchema](#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema)

Convert an TagResourceRequest to an TagResourceSchema.

Args:
: request: The request model version to convert.

Returns:
: The converted schema.

#### id *: UUID*

#### model *: Mapped[List[[ModelSchema](#zenml.zen_stores.schemas.model_schemas.ModelSchema)]]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'resource_id': FieldInfo(annotation=UUID, required=True), 'resource_type': FieldInfo(annotation=str, required=True), 'tag_id': FieldInfo(annotation=UUID, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_version *: Mapped[List[[ModelVersionSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema)]]*

#### resource_id *: UUID*

#### resource_type *: str*

#### tag *: Mapped[[TagSchema](#zenml.zen_stores.schemas.tag_schemas.TagSchema)]*

#### tag_id *: UUID*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [TagResourceResponse](zenml.models.v2.core.md#zenml.models.v2.core.tag_resource.TagResourceResponse)

Convert an TagResourceSchema to an TagResourceResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created TagResourceResponse.

#### updated *: datetime*

### *class* zenml.zen_stores.schemas.tag_schemas.TagSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, color: str)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for tag.

#### color *: str*

#### created *: datetime*

#### *classmethod* from_request(request: [TagRequest](zenml.models.v2.core.md#zenml.models.v2.core.tag.TagRequest)) → [TagSchema](#zenml.zen_stores.schemas.tag_schemas.TagSchema)

Convert an TagRequest to an TagSchema.

Args:
: request: The request model to convert.

Returns:
: The converted schema.

#### id *: UUID*

#### links *: Mapped[List[[TagResourceSchema](#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema)]]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'color': FieldInfo(annotation=str, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'name': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [TagResponse](zenml.models.v2.core.md#zenml.models.v2.core.tag.TagResponse)

Convert an TagSchema to an TagResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created TagResponse.

#### update(update: [TagUpdate](zenml.models.v2.core.md#zenml.models.v2.core.tag.TagUpdate)) → [TagSchema](#zenml.zen_stores.schemas.tag_schemas.TagSchema)

Updates a TagSchema from a TagUpdate.

Args:
: update: The TagUpdate to update from.

Returns:
: The updated TagSchema.

#### updated *: datetime*

## zenml.zen_stores.schemas.trigger_schemas module

SQL Model Implementations for Triggers.

### *class* zenml.zen_stores.schemas.trigger_schemas.TriggerExecutionSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, trigger_id: UUID, event_metadata: bytes | None = None)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

SQL Model for trigger executions.

#### created *: datetime*

#### event_metadata *: bytes | None*

#### *classmethod* from_request(request: [TriggerExecutionRequest](zenml.models.v2.core.md#zenml.models.v2.core.trigger_execution.TriggerExecutionRequest)) → [TriggerExecutionSchema](#zenml.zen_stores.schemas.trigger_schemas.TriggerExecutionSchema)

Convert a TriggerExecutionRequest to a TriggerExecutionSchema.

Args:
: request: The request model to convert.

Returns:
: The converted schema.

#### id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'event_metadata': FieldInfo(annotation=Union[bytes, NoneType], required=False, default=None), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'trigger_id': FieldInfo(annotation=UUID, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [TriggerExecutionResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger_execution.TriggerExecutionResponse)

Converts the schema to a model.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The converted model.

#### trigger *: Mapped[[TriggerSchema](#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema)]*

#### trigger_id *: UUID*

#### updated *: datetime*

### *class* zenml.zen_stores.schemas.trigger_schemas.TriggerSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, workspace_id: UUID, user_id: UUID | None, event_source_id: UUID | None, action_id: UUID, event_filter: bytes, schedule: bytes | None, description: str, is_active: bool)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for triggers.

#### action *: Mapped[[ActionSchema](#zenml.zen_stores.schemas.action_schemas.ActionSchema)]*

#### action_id *: UUID*

#### created *: datetime*

#### description *: str*

#### event_filter *: bytes*

#### event_source *: Mapped[[EventSourceSchema](#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema) | None]*

#### event_source_id *: UUID | None*

#### executions *: Mapped[List[[TriggerExecutionSchema](#zenml.zen_stores.schemas.trigger_schemas.TriggerExecutionSchema)]]*

#### *classmethod* from_request(request: [TriggerRequest](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerRequest)) → [TriggerSchema](#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema)

Convert a TriggerRequest to a TriggerSchema.

Args:
: request: The request model to convert.

Returns:
: The converted schema.

#### id *: UUID*

#### is_active *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'action_id': FieldInfo(annotation=UUID, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'description': FieldInfo(annotation=str, required=True), 'event_filter': FieldInfo(annotation=bytes, required=True), 'event_source_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'is_active': FieldInfo(annotation=bool, required=True), 'name': FieldInfo(annotation=str, required=True), 'schedule': FieldInfo(annotation=Union[bytes, NoneType], required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### schedule *: bytes | None*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [TriggerResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerResponse)

Converts the schema to a model.

Args:
: include_metadata: Flag deciding whether to include the output model(s)
  : metadata fields in the response.
  <br/>
  include_resources: Flag deciding whether to include the output model(s)
  : metadata fields in the response.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The converted model.

#### update(trigger_update: [TriggerUpdate](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerUpdate)) → [TriggerSchema](#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema)

Updates a trigger schema with a trigger update model.

Args:
: trigger_update: TriggerUpdate to update the trigger with.

Returns:
: The updated TriggerSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

## zenml.zen_stores.schemas.user_schemas module

SQLModel implementation of user tables.

### *class* zenml.zen_stores.schemas.user_schemas.UserSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, is_service_account: bool = False, full_name: str, description: str | None, email: str | None, active: bool, password: str | None, activation_token: str | None, email_opted_in: bool | None, external_user_id: UUID | None, is_admin: bool = False, user_metadata: str | None)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for users.

#### actions *: Mapped[List[[ActionSchema](#zenml.zen_stores.schemas.action_schemas.ActionSchema)]]*

#### activation_token *: str | None*

#### active *: bool*

#### api_keys *: Mapped[List[[APIKeySchema](#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema)]]*

#### artifact_versions *: Mapped[List[[ArtifactVersionSchema](#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema)]]*

#### auth_actions *: Mapped[List[[ActionSchema](#zenml.zen_stores.schemas.action_schemas.ActionSchema)]]*

#### auth_devices *: Mapped[List[[OAuthDeviceSchema](#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema)]]*

#### builds *: Mapped[List[[PipelineBuildSchema](#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema)]]*

#### code_repositories *: Mapped[List[[CodeRepositorySchema](#zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema)]]*

#### components *: Mapped[List[[StackComponentSchema](#zenml.zen_stores.schemas.component_schemas.StackComponentSchema)]]*

#### created *: datetime*

#### deployments *: Mapped[List[[PipelineDeploymentSchema](#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema)]]*

#### description *: str | None*

#### email *: str | None*

#### email_opted_in *: bool | None*

#### event_sources *: Mapped[List[[EventSourceSchema](#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema)]]*

#### external_user_id *: UUID | None*

#### flavors *: Mapped[List[[FlavorSchema](#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema)]]*

#### *classmethod* from_service_account_request(model: [ServiceAccountRequest](zenml.models.v2.core.md#zenml.models.v2.core.service_account.ServiceAccountRequest)) → [UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema)

Create a UserSchema from a Service Account request.

Args:
: model: The ServiceAccountRequest from which to create the
  : schema.

Returns:
: The created UserSchema.

#### *classmethod* from_user_request(model: [UserRequest](zenml.models.v2.core.md#zenml.models.v2.core.user.UserRequest)) → [UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema)

Create a UserSchema from a UserRequest.

Args:
: model: The UserRequest from which to create the schema.

Returns:
: The created UserSchema.

#### full_name *: str*

#### id *: UUID*

#### is_admin *: bool*

#### is_service_account *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'activation_token': FieldInfo(annotation=Union[str, NoneType], required=True), 'active': FieldInfo(annotation=bool, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'description': FieldInfo(annotation=Union[str, NoneType], required=True), 'email': FieldInfo(annotation=Union[str, NoneType], required=True), 'email_opted_in': FieldInfo(annotation=Union[bool, NoneType], required=True), 'external_user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'full_name': FieldInfo(annotation=str, required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'is_admin': FieldInfo(annotation=bool, required=False, default=False), 'is_service_account': FieldInfo(annotation=bool, required=False, default=False), 'name': FieldInfo(annotation=str, required=True), 'password': FieldInfo(annotation=Union[str, NoneType], required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_metadata': FieldInfo(annotation=Union[str, NoneType], required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_versions *: Mapped[List[[ModelVersionSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema)]]*

#### model_versions_artifacts_links *: Mapped[List[[ModelVersionArtifactSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema)]]*

#### model_versions_pipeline_runs_links *: Mapped[List[[ModelVersionPipelineRunSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema)]]*

#### models *: Mapped[List[[ModelSchema](#zenml.zen_stores.schemas.model_schemas.ModelSchema)]]*

#### name *: str*

#### password *: str | None*

#### pipelines *: Mapped[List[[PipelineSchema](#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema)]]*

#### run_metadata *: Mapped[List[[RunMetadataSchema](#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema)]]*

#### runs *: Mapped[List[[PipelineRunSchema](#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema)]]*

#### schedules *: Mapped[List[[ScheduleSchema](#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema)]]*

#### secrets *: Mapped[List[[SecretSchema](#zenml.zen_stores.schemas.secret_schemas.SecretSchema)]]*

#### service_connectors *: Mapped[List[[ServiceConnectorSchema](#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema)]]*

#### services *: Mapped[List[[ServiceSchema](#zenml.zen_stores.schemas.service_schemas.ServiceSchema)]]*

#### stacks *: Mapped[List[[StackSchema](#zenml.zen_stores.schemas.stack_schemas.StackSchema)]]*

#### step_runs *: Mapped[List[[StepRunSchema](#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema)]]*

#### to_model(include_metadata: bool = False, include_resources: bool = False, include_private: bool = False, \*\*kwargs: Any) → [UserResponse](zenml.models.v2.core.md#zenml.models.v2.core.user.UserResponse)

Convert a UserSchema to a UserResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic
  include_private: Whether to include the user private information
  <br/>
  > this is to limit the amount of data one can get
  > about other users

Returns:
: The converted UserResponse.

#### to_service_account_model(include_metadata: bool = False, include_resources: bool = False) → [ServiceAccountResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_account.ServiceAccountResponse)

Convert a UserSchema to a ServiceAccountResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.

Returns:
: The converted ServiceAccountResponse.

#### triggers *: Mapped[List[[TriggerSchema](#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema)]]*

#### update_service_account(service_account_update: [ServiceAccountUpdate](zenml.models.v2.core.md#zenml.models.v2.core.service_account.ServiceAccountUpdate)) → [UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema)

Update a UserSchema from a ServiceAccountUpdate.

Args:
: service_account_update: The ServiceAccountUpdate from which
  : to update the schema.

Returns:
: The updated UserSchema.

#### update_user(user_update: [UserUpdate](zenml.models.v2.core.md#zenml.models.v2.core.user.UserUpdate)) → [UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema)

Update a UserSchema from a UserUpdate.

Args:
: user_update: The UserUpdate from which to update the schema.

Returns:
: The updated UserSchema.

#### updated *: datetime*

#### user_metadata *: str | None*

## zenml.zen_stores.schemas.utils module

Utils for schemas.

### zenml.zen_stores.schemas.utils.get_page_from_list(items_list: List[S], response_model: Type[[BaseResponse](zenml.models.v2.base.md#id248)], size: int = 5, page: int = 1, include_resources: bool = False, include_metadata: bool = False) → [Page](zenml.models.v2.base.md#id327)[[BaseResponse](zenml.models.md#zenml.models.BaseResponse)]

Converts list of schemas into page of response models.

Args:
: items_list: List of schemas
  response_model: Response model
  size: Page size
  page: Page number
  include_metadata: Whether metadata should be included in response models
  include_resources: Whether resources should be included in response models

Returns:
: A page of list items.

## zenml.zen_stores.schemas.workspace_schemas module

SQL Model Implementations for Workspaces.

### *class* zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, description: str)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for workspaces.

#### actions *: Mapped[List[[ActionSchema](#zenml.zen_stores.schemas.action_schemas.ActionSchema)]]*

#### artifact_versions *: Mapped[List[[ArtifactVersionSchema](#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema)]]*

#### builds *: Mapped[List[[PipelineBuildSchema](#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema)]]*

#### code_repositories *: Mapped[List[[CodeRepositorySchema](#zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema)]]*

#### components *: Mapped[List[[StackComponentSchema](#zenml.zen_stores.schemas.component_schemas.StackComponentSchema)]]*

#### created *: datetime*

#### deployments *: Mapped[List[[PipelineDeploymentSchema](#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema)]]*

#### description *: str*

#### event_sources *: Mapped[List[[EventSourceSchema](#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema)]]*

#### flavors *: Mapped[List[[FlavorSchema](#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema)]]*

#### *classmethod* from_request(workspace: [WorkspaceRequest](zenml.models.v2.core.md#zenml.models.v2.core.workspace.WorkspaceRequest)) → [WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)

Create a WorkspaceSchema from a WorkspaceResponse.

Args:
: workspace: The WorkspaceResponse from which to create the schema.

Returns:
: The created WorkspaceSchema.

#### id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'description': FieldInfo(annotation=str, required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'name': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_versions *: Mapped[List[[ModelVersionSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema)]]*

#### model_versions_artifacts_links *: Mapped[List[[ModelVersionArtifactSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema)]]*

#### model_versions_pipeline_runs_links *: Mapped[List[[ModelVersionPipelineRunSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema)]]*

#### models *: Mapped[List[[ModelSchema](#zenml.zen_stores.schemas.model_schemas.ModelSchema)]]*

#### name *: str*

#### pipelines *: Mapped[List[[PipelineSchema](#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema)]]*

#### run_metadata *: Mapped[List[[RunMetadataSchema](#zenml.zen_stores.schemas.run_metadata_schemas.RunMetadataSchema)]]*

#### runs *: Mapped[List[[PipelineRunSchema](#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema)]]*

#### schedules *: Mapped[List[[ScheduleSchema](#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema)]]*

#### secrets *: Mapped[List[[SecretSchema](#zenml.zen_stores.schemas.secret_schemas.SecretSchema)]]*

#### service_connectors *: Mapped[List[[ServiceConnectorSchema](#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema)]]*

#### services *: Mapped[List[[ServiceSchema](#zenml.zen_stores.schemas.service_schemas.ServiceSchema)]]*

#### stacks *: Mapped[List[[StackSchema](#zenml.zen_stores.schemas.stack_schemas.StackSchema)]]*

#### step_runs *: Mapped[List[[StepRunSchema](#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema)]]*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [WorkspaceResponse](zenml.models.v2.core.md#zenml.models.v2.core.workspace.WorkspaceResponse)

Convert a WorkspaceSchema to a WorkspaceResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The converted WorkspaceResponseModel.

#### triggers *: Mapped[List[[TriggerSchema](#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema)]]*

#### update(workspace_update: [WorkspaceUpdate](zenml.models.v2.core.md#zenml.models.v2.core.workspace.WorkspaceUpdate)) → [WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)

Update a WorkspaceSchema from a WorkspaceUpdate.

Args:
: workspace_update: The WorkspaceUpdate from which to update the
  : schema.

Returns:
: The updated WorkspaceSchema.

#### updated *: datetime*

## Module contents

SQL Model Implementations.

### *class* zenml.zen_stores.schemas.APIKeySchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, description: str, key: str, previous_key: str | None = None, retain_period: int = 0, active: bool = True, last_login: datetime | None = None, last_rotated: datetime | None = None, service_account_id: UUID)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for API keys.

#### active *: bool*

#### created *: datetime*

#### description *: str*

#### *classmethod* from_request(service_account_id: UUID, request: [APIKeyRequest](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyRequest)) → Tuple[[APIKeySchema](#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema), str]

Convert a APIKeyRequest to a APIKeySchema.

Args:
: service_account_id: The service account id to associate the key
  : with.
  <br/>
  request: The request model to convert.

Returns:
: The converted schema and the un-hashed API key.

#### id *: UUID*

#### internal_update(update: [APIKeyInternalUpdate](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyInternalUpdate)) → [APIKeySchema](#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema)

Update an APIKeySchema with an APIKeyInternalUpdate.

The internal update can also update the last used timestamp.

Args:
: update: The update model.

Returns:
: The updated APIKeySchema.

#### key *: str*

#### last_login *: datetime | None*

#### last_rotated *: datetime | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'active': FieldInfo(annotation=bool, required=False, default=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'description': FieldInfo(annotation=str, required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'key': FieldInfo(annotation=str, required=True), 'last_login': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'last_rotated': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'name': FieldInfo(annotation=str, required=True), 'previous_key': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'retain_period': FieldInfo(annotation=int, required=False, default=0), 'service_account_id': FieldInfo(annotation=UUID, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### previous_key *: str | None*

#### retain_period *: int*

#### rotate(rotate_request: [APIKeyRotateRequest](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyRotateRequest)) → Tuple[[APIKeySchema](#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema), str]

Rotate the key for an APIKeySchema.

Args:
: rotate_request: The rotate request model.

Returns:
: The updated APIKeySchema and the new un-hashed key.

#### service_account *: Mapped[[UserSchema](#zenml.zen_stores.schemas.UserSchema)]*

#### service_account_id *: UUID*

#### to_internal_model(hydrate: bool = False) → [APIKeyInternalResponse](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyInternalResponse)

Convert a APIKeySchema to an APIKeyInternalResponse.

The internal response model includes the hashed key values.

Args:
: hydrate: bool to decide whether to return a hydrated version of the
  : model.

Returns:
: The created APIKeyInternalResponse.

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [APIKeyResponse](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyResponse)

Convert a APIKeySchema to an APIKeyResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to filter models.

Returns:
: The created APIKeyResponse.

#### update(update: [APIKeyUpdate](zenml.models.v2.core.md#zenml.models.v2.core.api_key.APIKeyUpdate)) → [APIKeySchema](#zenml.zen_stores.schemas.api_key_schemas.APIKeySchema)

Update an APIKeySchema with an APIKeyUpdate.

Args:
: update: The update model.

Returns:
: The updated APIKeySchema.

#### updated *: datetime*

### *class* zenml.zen_stores.schemas.ActionSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, workspace_id: UUID, user_id: UUID | None, service_account_id: UUID, auth_window: int, flavor: str, plugin_subtype: str, description: str | None, configuration: bytes)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for actions.

#### auth_window *: int*

#### configuration *: bytes*

#### created *: datetime*

#### description *: str | None*

#### flavor *: str*

#### *classmethod* from_request(request: [ActionRequest](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionRequest)) → [ActionSchema](#zenml.zen_stores.schemas.action_schemas.ActionSchema)

Convert a ActionRequest to a ActionSchema.

Args:
: request: The request model to convert.

Returns:
: The converted schema.

#### id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'auth_window': FieldInfo(annotation=int, required=True), 'configuration': FieldInfo(annotation=bytes, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'description': FieldInfo(annotation=Union[str, NoneType], required=True), 'flavor': FieldInfo(annotation=str, required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'name': FieldInfo(annotation=str, required=True), 'plugin_subtype': FieldInfo(annotation=str, required=True), 'service_account_id': FieldInfo(annotation=UUID, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### plugin_subtype *: str*

#### service_account *: Mapped[[UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema)]*

#### service_account_id *: UUID*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [ActionResponse](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionResponse)

Converts the action schema to a model.

Args:
: include_metadata: Flag deciding whether to include the output model(s)
  : metadata fields in the response.
  <br/>
  include_resources: Flag deciding whether to include the output model(s)
  : metadata fields in the response.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The converted model.

#### triggers *: Mapped[List[[TriggerSchema](#zenml.zen_stores.schemas.TriggerSchema)]]*

#### update(action_update: [ActionUpdate](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionUpdate)) → [ActionSchema](#zenml.zen_stores.schemas.action_schemas.ActionSchema)

Updates a action schema with a action update model.

Args:
: action_update: ActionUpdate to update the action with.

Returns:
: The updated ActionSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

### *class* zenml.zen_stores.schemas.ArtifactSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, has_custom_name: bool)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for artifacts.

#### created *: datetime*

#### *classmethod* from_request(artifact_request: [ArtifactRequest](zenml.models.v2.core.md#zenml.models.v2.core.artifact.ArtifactRequest)) → [ArtifactSchema](#zenml.zen_stores.schemas.artifact_schemas.ArtifactSchema)

Convert an ArtifactRequest to an ArtifactSchema.

Args:
: artifact_request: The request model to convert.

Returns:
: The converted schema.

#### has_custom_name *: bool*

#### id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'has_custom_name': FieldInfo(annotation=bool, required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'name': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### tags *: Mapped[List[[TagResourceSchema](#zenml.zen_stores.schemas.TagResourceSchema)]]*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [ArtifactResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact.ArtifactResponse)

Convert an ArtifactSchema to an ArtifactResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created ArtifactResponse.

#### update(artifact_update: [ArtifactUpdate](zenml.models.v2.core.md#zenml.models.v2.core.artifact.ArtifactUpdate)) → [ArtifactSchema](#zenml.zen_stores.schemas.artifact_schemas.ArtifactSchema)

Update an ArtifactSchema with an ArtifactUpdate.

Args:
: artifact_update: The update model to apply.

Returns:
: The updated ArtifactSchema.

#### updated *: datetime*

#### versions *: Mapped[List[[ArtifactVersionSchema](#zenml.zen_stores.schemas.ArtifactVersionSchema)]]*

### *class* zenml.zen_stores.schemas.ArtifactVersionSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, version: str, version_number: int | None, type: str, uri: str, materializer: str, data_type: str, artifact_id: UUID, artifact_store_id: UUID | None, user_id: UUID | None, workspace_id: UUID)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

SQL Model for artifact versions.

#### artifact *: Mapped[[ArtifactSchema](#zenml.zen_stores.schemas.ArtifactSchema)]*

#### artifact_id *: UUID*

#### artifact_store_id *: UUID | None*

#### created *: datetime*

#### data_type *: str*

#### *classmethod* from_request(artifact_version_request: [ArtifactVersionRequest](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionRequest)) → [ArtifactVersionSchema](#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema)

Convert an ArtifactVersionRequest to an ArtifactVersionSchema.

Args:
: artifact_version_request: The request model to convert.

Returns:
: The converted schema.

#### id *: UUID*

#### input_of_step_runs *: Mapped[List[[StepRunInputArtifactSchema](#zenml.zen_stores.schemas.StepRunInputArtifactSchema)]]*

#### materializer *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact_id': FieldInfo(annotation=UUID, required=True), 'artifact_store_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'data_type': FieldInfo(annotation=str, required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'materializer': FieldInfo(annotation=str, required=True), 'type': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'uri': FieldInfo(annotation=str, required=True), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'version': FieldInfo(annotation=str, required=True), 'version_number': FieldInfo(annotation=Union[int, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_versions_artifacts_links *: Mapped[List[[ModelVersionArtifactSchema](#zenml.zen_stores.schemas.ModelVersionArtifactSchema)]]*

#### output_of_step_runs *: Mapped[List[[StepRunOutputArtifactSchema](#zenml.zen_stores.schemas.StepRunOutputArtifactSchema)]]*

#### run_metadata *: Mapped[List[[RunMetadataSchema](#zenml.zen_stores.schemas.RunMetadataSchema)]]*

#### tags *: Mapped[List[[TagResourceSchema](#zenml.zen_stores.schemas.TagResourceSchema)]]*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [ArtifactVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionResponse)

Convert an ArtifactVersionSchema to an ArtifactVersionResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created ArtifactVersionResponse.

#### type *: str*

#### update(artifact_version_update: [ArtifactVersionUpdate](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionUpdate)) → [ArtifactVersionSchema](#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema)

Update an ArtifactVersionSchema with an ArtifactVersionUpdate.

Args:
: artifact_version_update: The update model to apply.

Returns:
: The updated ArtifactVersionSchema.

#### updated *: datetime*

#### uri *: str*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### version *: str*

#### version_number *: int | None*

#### visualizations *: Mapped[List[[ArtifactVisualizationSchema](#zenml.zen_stores.schemas.ArtifactVisualizationSchema)]]*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

### *class* zenml.zen_stores.schemas.ArtifactVisualizationSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, type: str, uri: str, artifact_version_id: UUID)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

SQL Model for visualizations of artifacts.

#### artifact_version *: Mapped[[ArtifactVersionSchema](#zenml.zen_stores.schemas.artifact_schemas.ArtifactVersionSchema)]*

#### artifact_version_id *: UUID*

#### created *: datetime*

#### *classmethod* from_model(artifact_visualization_request: [ArtifactVisualizationRequest](zenml.models.v2.core.md#zenml.models.v2.core.artifact_visualization.ArtifactVisualizationRequest), artifact_version_id: UUID) → [ArtifactVisualizationSchema](#zenml.zen_stores.schemas.artifact_visualization_schemas.ArtifactVisualizationSchema)

Convert a ArtifactVisualizationRequest to a ArtifactVisualizationSchema.

Args:
: artifact_visualization_request: The visualization.
  artifact_version_id: The UUID of the artifact version.

Returns:
: The ArtifactVisualizationSchema.

#### id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact_version_id': FieldInfo(annotation=UUID, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'type': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'uri': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [ArtifactVisualizationResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact_visualization.ArtifactVisualizationResponse)

Convert an ArtifactVisualizationSchema to a Visualization.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The Visualization.

#### type *: str*

#### updated *: datetime*

#### uri *: str*

### *class* zenml.zen_stores.schemas.BaseSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None)

Bases: `SQLModel`

Base SQL Model for ZenML entities.

#### created *: datetime*

#### id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'registry': PydanticUndefined}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → Any

In case the Schema has a corresponding Model, this allows conversion to that model.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Raises:
: NotImplementedError: When the base class fails to implement this.

#### updated *: datetime*

### *class* zenml.zen_stores.schemas.CodeReferenceSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, workspace_id: UUID, code_repository_id: UUID, commit: str, subdirectory: str)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

SQL Model for code references.

#### code_repository *: Mapped[[CodeRepositorySchema](#zenml.zen_stores.schemas.CodeRepositorySchema)]*

#### code_repository_id *: UUID*

#### commit *: str*

#### created *: datetime*

#### *classmethod* from_request(request: [CodeReferenceRequest](zenml.models.v2.core.md#zenml.models.v2.core.code_reference.CodeReferenceRequest), workspace_id: UUID) → [CodeReferenceSchema](#zenml.zen_stores.schemas.code_repository_schemas.CodeReferenceSchema)

Convert a CodeReferenceRequest to a CodeReferenceSchema.

Args:
: request: The request model to convert.
  workspace_id: The workspace ID.

Returns:
: The converted schema.

#### id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'code_repository_id': FieldInfo(annotation=UUID, required=True), 'commit': FieldInfo(annotation=str, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'subdirectory': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### subdirectory *: str*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [CodeReferenceResponse](zenml.models.v2.core.md#zenml.models.v2.core.code_reference.CodeReferenceResponse)

Convert a CodeReferenceSchema to a CodeReferenceResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic
  <br/>
  kwargs: Additional keyword arguments.

Returns:
: The converted model.

#### updated *: datetime*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

### *class* zenml.zen_stores.schemas.CodeRepositorySchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, workspace_id: UUID, user_id: UUID | None, config: str, source: str, logo_url: str | None, description: str | None)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for code repositories.

#### config *: str*

#### created *: datetime*

#### description *: str | None*

#### *classmethod* from_request(request: [CodeRepositoryRequest](zenml.models.v2.core.md#zenml.models.v2.core.code_repository.CodeRepositoryRequest)) → [CodeRepositorySchema](#zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema)

Convert a CodeRepositoryRequest to a CodeRepositorySchema.

Args:
: request: The request model to convert.

Returns:
: The converted schema.

#### id *: UUID*

#### logo_url *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config': FieldInfo(annotation=str, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'description': FieldInfo(annotation=Union[str, NoneType], required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'logo_url': FieldInfo(annotation=Union[str, NoneType], required=True), 'name': FieldInfo(annotation=str, required=True), 'source': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### source *: str*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [CodeRepositoryResponse](zenml.models.v2.core.md#zenml.models.v2.core.code_repository.CodeRepositoryResponse)

Convert a CodeRepositorySchema to a CodeRepositoryResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created CodeRepositoryResponse.

#### update(update: [CodeRepositoryUpdate](zenml.models.v2.core.md#zenml.models.v2.core.code_repository.CodeRepositoryUpdate)) → [CodeRepositorySchema](#zenml.zen_stores.schemas.code_repository_schemas.CodeRepositorySchema)

Update a CodeRepositorySchema with a CodeRepositoryUpdate.

Args:
: update: The update model.

Returns:
: The updated CodeRepositorySchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

### *class* zenml.zen_stores.schemas.EventSourceSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, workspace_id: UUID, user_id: UUID | None, flavor: str, plugin_subtype: str, description: str, configuration: bytes, is_active: bool)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for tag.

#### configuration *: bytes*

#### created *: datetime*

#### description *: str*

#### flavor *: str*

#### *classmethod* from_request(request: [EventSourceRequest](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceRequest)) → [EventSourceSchema](#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema)

Convert an EventSourceRequest to an EventSourceSchema.

Args:
: request: The request model to convert.

Returns:
: The converted schema.

#### id *: UUID*

#### is_active *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'configuration': FieldInfo(annotation=bytes, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'description': FieldInfo(annotation=str, required=True), 'flavor': FieldInfo(annotation=str, required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'is_active': FieldInfo(annotation=bool, required=True), 'name': FieldInfo(annotation=str, required=True), 'plugin_subtype': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### plugin_subtype *: str*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [EventSourceResponse](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceResponse)

Convert an EventSourceSchema to an EventSourceResponse.

Args:
: include_metadata: Flag deciding whether to include the output model(s)
  : metadata fields in the response.
  <br/>
  include_resources: Flag deciding whether to include the output model(s)
  : metadata fields in the response.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created EventSourceResponse.

#### triggers *: Mapped[List[[TriggerSchema](#zenml.zen_stores.schemas.TriggerSchema)]]*

#### update(update: [EventSourceUpdate](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceUpdate)) → [EventSourceSchema](#zenml.zen_stores.schemas.event_source_schemas.EventSourceSchema)

Updates a EventSourceSchema from a EventSourceUpdate.

Args:
: update: The EventSourceUpdate to update from.

Returns:
: The updated EventSourceSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

### *class* zenml.zen_stores.schemas.FlavorSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, type: str, source: str, config_schema: str, integration: str | None = '', connector_type: str | None, connector_resource_type: str | None, connector_resource_id_attr: str | None, workspace_id: UUID | None, user_id: UUID | None, logo_url: str | None, docs_url: str | None, sdk_docs_url: str | None, is_custom: bool = True)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for flavors.

Attributes:
: type: The type of the flavor.
  source: The source of the flavor.
  config_schema: The config schema of the flavor.
  integration: The integration associated with the flavor.

#### config_schema *: str*

#### connector_resource_id_attr *: str | None*

#### connector_resource_type *: str | None*

#### connector_type *: str | None*

#### created *: datetime*

#### docs_url *: str | None*

#### id *: UUID*

#### integration *: str | None*

#### is_custom *: bool*

#### logo_url *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config_schema': FieldInfo(annotation=str, required=True), 'connector_resource_id_attr': FieldInfo(annotation=Union[str, NoneType], required=True), 'connector_resource_type': FieldInfo(annotation=Union[str, NoneType], required=True), 'connector_type': FieldInfo(annotation=Union[str, NoneType], required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'docs_url': FieldInfo(annotation=Union[str, NoneType], required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'integration': FieldInfo(annotation=Union[str, NoneType], required=False, default=''), 'is_custom': FieldInfo(annotation=bool, required=False, default=True), 'logo_url': FieldInfo(annotation=Union[str, NoneType], required=True), 'name': FieldInfo(annotation=str, required=True), 'sdk_docs_url': FieldInfo(annotation=Union[str, NoneType], required=True), 'source': FieldInfo(annotation=str, required=True), 'type': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=Union[UUID, NoneType], required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### sdk_docs_url *: str | None*

#### source *: str*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [FlavorResponse](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorResponse)

Converts a flavor schema to a flavor model.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The flavor model.

#### type *: str*

#### update(flavor_update: [FlavorUpdate](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorUpdate)) → [FlavorSchema](#zenml.zen_stores.schemas.flavor_schemas.FlavorSchema)

Update a FlavorSchema from a FlavorUpdate.

Args:
: flavor_update: The FlavorUpdate from which to update the schema.

Returns:
: The updated FlavorSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.WorkspaceSchema) | None]*

#### workspace_id *: UUID | None*

### *class* zenml.zen_stores.schemas.LogsSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, uri: str, pipeline_run_id: UUID | None, step_run_id: UUID | None, artifact_store_id: UUID)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

SQL Model for logs.

#### artifact_store *: Mapped[[StackComponentSchema](#zenml.zen_stores.schemas.StackComponentSchema) | None]*

#### artifact_store_id *: UUID*

#### created *: datetime*

#### id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact_store_id': FieldInfo(annotation=UUID, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'pipeline_run_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'step_run_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'uri': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### pipeline_run *: Mapped[[PipelineRunSchema](#zenml.zen_stores.schemas.PipelineRunSchema) | None]*

#### pipeline_run_id *: UUID | None*

#### step_run *: Mapped[[StepRunSchema](#zenml.zen_stores.schemas.StepRunSchema) | None]*

#### step_run_id *: UUID | None*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [LogsResponse](zenml.models.v2.core.md#zenml.models.v2.core.logs.LogsResponse)

Convert a LogsSchema to a LogsResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created LogsResponse.

#### updated *: datetime*

#### uri *: str*

### *class* zenml.zen_stores.schemas.ModelSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, workspace_id: UUID, user_id: UUID | None, license: str, description: str, audience: str, use_cases: str, limitations: str, trade_offs: str, ethics: str, save_models_to_registry: bool)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for model.

#### artifact_links *: Mapped[List[[ModelVersionArtifactSchema](#zenml.zen_stores.schemas.ModelVersionArtifactSchema)]]*

#### audience *: str*

#### created *: datetime*

#### description *: str*

#### ethics *: str*

#### *classmethod* from_request(model_request: [ModelRequest](zenml.models.v2.core.md#zenml.models.v2.core.model.ModelRequest)) → [ModelSchema](#zenml.zen_stores.schemas.model_schemas.ModelSchema)

Convert an ModelRequest to an ModelSchema.

Args:
: model_request: The request model to convert.

Returns:
: The converted schema.

#### id *: UUID*

#### license *: str*

#### limitations *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'audience': FieldInfo(annotation=str, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'description': FieldInfo(annotation=str, required=True), 'ethics': FieldInfo(annotation=str, required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'license': FieldInfo(annotation=str, required=True), 'limitations': FieldInfo(annotation=str, required=True), 'name': FieldInfo(annotation=str, required=True), 'save_models_to_registry': FieldInfo(annotation=bool, required=True), 'trade_offs': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'use_cases': FieldInfo(annotation=str, required=True), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_versions *: Mapped[List[[ModelVersionSchema](#zenml.zen_stores.schemas.ModelVersionSchema)]]*

#### name *: str*

#### pipeline_run_links *: Mapped[List[[ModelVersionPipelineRunSchema](#zenml.zen_stores.schemas.ModelVersionPipelineRunSchema)]]*

#### save_models_to_registry *: bool*

#### tags *: Mapped[List[[TagResourceSchema](#zenml.zen_stores.schemas.TagResourceSchema)]]*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [ModelResponse](zenml.models.v2.core.md#zenml.models.v2.core.model.ModelResponse)

Convert an ModelSchema to an ModelResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created ModelResponse.

#### trade_offs *: str*

#### update(model_update: [ModelUpdate](zenml.models.v2.core.md#zenml.models.v2.core.model.ModelUpdate)) → [ModelSchema](#zenml.zen_stores.schemas.model_schemas.ModelSchema)

Updates a ModelSchema from a ModelUpdate.

Args:
: model_update: The ModelUpdate to update from.

Returns:
: The updated ModelSchema.

#### updated *: datetime*

#### use_cases *: str*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

### *class* zenml.zen_stores.schemas.ModelVersionArtifactSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, workspace_id: UUID, user_id: UUID | None, model_id: UUID, model_version_id: UUID, artifact_version_id: UUID, is_model_artifact: bool, is_deployment_artifact: bool)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

SQL Model for linking of Model Versions and Artifacts M:M.

#### artifact_version *: Mapped[[ArtifactVersionSchema](#zenml.zen_stores.schemas.ArtifactVersionSchema)]*

#### artifact_version_id *: UUID*

#### created *: datetime*

#### *classmethod* from_request(model_version_artifact_request: [ModelVersionArtifactRequest](zenml.models.v2.core.md#zenml.models.v2.core.model_version_artifact.ModelVersionArtifactRequest)) → [ModelVersionArtifactSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionArtifactSchema)

Convert an ModelVersionArtifactRequest to a ModelVersionArtifactSchema.

Args:
: model_version_artifact_request: The request link to convert.

Returns:
: The converted schema.

#### id *: UUID*

#### is_deployment_artifact *: bool*

#### is_model_artifact *: bool*

#### model *: Mapped[[ModelSchema](#zenml.zen_stores.schemas.ModelSchema)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'protected_namespaces': (), 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact_version_id': FieldInfo(annotation=UUID, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'is_deployment_artifact': FieldInfo(annotation=bool, required=True), 'is_model_artifact': FieldInfo(annotation=bool, required=True), 'model_id': FieldInfo(annotation=UUID, required=True), 'model_version_id': FieldInfo(annotation=UUID, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_id *: UUID*

#### model_version *: Mapped[[ModelVersionSchema](#zenml.zen_stores.schemas.ModelVersionSchema)]*

#### model_version_id *: UUID*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [ModelVersionArtifactResponse](zenml.models.v2.core.md#zenml.models.v2.core.model_version_artifact.ModelVersionArtifactResponse)

Convert an ModelVersionArtifactSchema to an ModelVersionArtifactResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created ModelVersionArtifactResponseModel.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

### *class* zenml.zen_stores.schemas.ModelVersionPipelineRunSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, workspace_id: UUID, user_id: UUID | None, model_id: UUID, model_version_id: UUID, pipeline_run_id: UUID)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

SQL Model for linking of Model Versions and Pipeline Runs M:M.

#### created *: datetime*

#### *classmethod* from_request(model_version_pipeline_run_request: [ModelVersionPipelineRunRequest](zenml.models.v2.core.md#zenml.models.v2.core.model_version_pipeline_run.ModelVersionPipelineRunRequest)) → [ModelVersionPipelineRunSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionPipelineRunSchema)

Convert an ModelVersionPipelineRunRequest to an ModelVersionPipelineRunSchema.

Args:
: model_version_pipeline_run_request: The request link to convert.

Returns:
: The converted schema.

#### id *: UUID*

#### model *: Mapped[[ModelSchema](#zenml.zen_stores.schemas.ModelSchema)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'protected_namespaces': (), 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'model_id': FieldInfo(annotation=UUID, required=True), 'model_version_id': FieldInfo(annotation=UUID, required=True), 'pipeline_run_id': FieldInfo(annotation=UUID, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_id *: UUID*

#### model_version *: Mapped[[ModelVersionSchema](#zenml.zen_stores.schemas.ModelVersionSchema)]*

#### model_version_id *: UUID*

#### pipeline_run *: Mapped[[PipelineRunSchema](#zenml.zen_stores.schemas.PipelineRunSchema)]*

#### pipeline_run_id *: UUID*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [ModelVersionPipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.model_version_pipeline_run.ModelVersionPipelineRunResponse)

Convert an ModelVersionPipelineRunSchema to an ModelVersionPipelineRunResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created ModelVersionPipelineRunResponse.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

### *class* zenml.zen_stores.schemas.ModelVersionSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, workspace_id: UUID, user_id: UUID | None, model_id: UUID, number: int, description: str, stage: str)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for model version.

#### artifact_links *: Mapped[List[[ModelVersionArtifactSchema](#zenml.zen_stores.schemas.ModelVersionArtifactSchema)]]*

#### created *: datetime*

#### description *: str*

#### *classmethod* from_request(model_version_request: [ModelVersionRequest](zenml.models.v2.core.md#zenml.models.v2.core.model_version.ModelVersionRequest)) → [ModelVersionSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema)

Convert an ModelVersionRequest to an ModelVersionSchema.

Args:
: model_version_request: The request model version to convert.

Returns:
: The converted schema.

#### id *: UUID*

#### model *: Mapped[[ModelSchema](#zenml.zen_stores.schemas.ModelSchema)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'protected_namespaces': (), 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'description': FieldInfo(annotation=str, required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'model_id': FieldInfo(annotation=UUID, required=True), 'name': FieldInfo(annotation=str, required=True), 'number': FieldInfo(annotation=int, required=True), 'stage': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_id *: UUID*

#### name *: str*

#### number *: int*

#### pipeline_run_links *: Mapped[List[[ModelVersionPipelineRunSchema](#zenml.zen_stores.schemas.ModelVersionPipelineRunSchema)]]*

#### pipeline_runs *: Mapped[List[[PipelineRunSchema](#zenml.zen_stores.schemas.PipelineRunSchema)]]*

#### run_metadata *: Mapped[List[[RunMetadataSchema](#zenml.zen_stores.schemas.RunMetadataSchema)]]*

#### services *: Mapped[List[[ServiceSchema](#zenml.zen_stores.schemas.ServiceSchema)]]*

#### stage *: str*

#### step_runs *: Mapped[List[[StepRunSchema](#zenml.zen_stores.schemas.StepRunSchema)]]*

#### tags *: Mapped[List[[TagResourceSchema](#zenml.zen_stores.schemas.TagResourceSchema)]]*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [ModelVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.model_version.ModelVersionResponse)

Convert an ModelVersionSchema to an ModelVersionResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created ModelVersionResponse.

#### update(target_stage: str | None = None, target_name: str | None = None, target_description: str | None = None) → [ModelVersionSchema](#zenml.zen_stores.schemas.model_schemas.ModelVersionSchema)

Updates a ModelVersionSchema to a target stage.

Args:
: target_stage: The stage to be updated.
  target_name: The version name to be updated.
  target_description: The version description to be updated.

Returns:
: The updated ModelVersionSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

### *class* zenml.zen_stores.schemas.NamedSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

Base Named SQL Model.

#### created *: datetime*

#### id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'registry': PydanticUndefined}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'name': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### updated *: datetime*

### *class* zenml.zen_stores.schemas.OAuthDeviceSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, client_id: UUID, user_code: str, device_code: str, status: str, failed_auth_attempts: int = 0, expires: datetime | None = None, last_login: datetime | None = None, trusted_device: bool = False, os: str | None = None, ip_address: str | None = None, hostname: str | None = None, python_version: str | None = None, zenml_version: str | None = None, city: str | None = None, region: str | None = None, country: str | None = None, user_id: UUID | None)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

SQL Model for authorized OAuth2 devices.

#### city *: str | None*

#### client_id *: UUID*

#### country *: str | None*

#### created *: datetime*

#### device_code *: str*

#### expires *: datetime | None*

#### failed_auth_attempts *: int*

#### *classmethod* from_request(request: [OAuthDeviceInternalRequest](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceInternalRequest)) → Tuple[[OAuthDeviceSchema](#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema), str, str]

Create an authorized device DB entry from a device authorization request.

Args:
: request: The device authorization request.

Returns:
: The created OAuthDeviceSchema, the user code and the device code.

#### hostname *: str | None*

#### id *: UUID*

#### internal_update(device_update: [OAuthDeviceInternalUpdate](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceInternalUpdate)) → Tuple[[OAuthDeviceSchema](#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema), str | None, str | None]

Update an authorized device from an internal device update model.

Args:
: device_update: The internal device update model.

Returns:
: The updated OAuthDeviceSchema and the new user code and device
  code, if they were generated.

#### ip_address *: str | None*

#### last_login *: datetime | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'city': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'client_id': FieldInfo(annotation=UUID, required=True), 'country': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'device_code': FieldInfo(annotation=str, required=True), 'expires': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'failed_auth_attempts': FieldInfo(annotation=int, required=False, default=0), 'hostname': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'ip_address': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'last_login': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'os': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'python_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'region': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'status': FieldInfo(annotation=str, required=True), 'trusted_device': FieldInfo(annotation=bool, required=False, default=False), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_code': FieldInfo(annotation=str, required=True), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'zenml_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### os *: str | None*

#### python_version *: str | None*

#### region *: str | None*

#### status *: str*

#### to_internal_model(hydrate: bool = False) → [OAuthDeviceInternalResponse](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceInternalResponse)

Convert a device schema to an internal device response model.

Args:
: hydrate: bool to decide whether to return a hydrated version of the
  : model.

Returns:
: The converted internal device response model.

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [OAuthDeviceResponse](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceResponse)

Convert a device schema to a device response model.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The converted device response model.

#### trusted_device *: bool*

#### update(device_update: [OAuthDeviceUpdate](zenml.models.v2.core.md#zenml.models.v2.core.device.OAuthDeviceUpdate)) → [OAuthDeviceSchema](#zenml.zen_stores.schemas.device_schemas.OAuthDeviceSchema)

Update an authorized device from a device update model.

Args:
: device_update: The device update model.

Returns:
: The updated OAuthDeviceSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.UserSchema) | None]*

#### user_code *: str*

#### user_id *: UUID | None*

#### zenml_version *: str | None*

### *class* zenml.zen_stores.schemas.PipelineBuildSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, user_id: UUID | None, workspace_id: UUID, stack_id: UUID | None, pipeline_id: UUID | None, images: str, is_local: bool, contains_code: bool, zenml_version: str | None, python_version: str | None, checksum: str | None, stack_checksum: str | None)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

SQL Model for pipeline builds.

#### checksum *: str | None*

#### contains_code *: bool*

#### created *: datetime*

#### *classmethod* from_request(request: [PipelineBuildRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_build.PipelineBuildRequest)) → [PipelineBuildSchema](#zenml.zen_stores.schemas.pipeline_build_schemas.PipelineBuildSchema)

Convert a PipelineBuildRequest to a PipelineBuildSchema.

Args:
: request: The request to convert.

Returns:
: The created PipelineBuildSchema.

#### id *: UUID*

#### images *: str*

#### is_local *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'checksum': FieldInfo(annotation=Union[str, NoneType], required=True), 'contains_code': FieldInfo(annotation=bool, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'images': FieldInfo(annotation=str, required=True), 'is_local': FieldInfo(annotation=bool, required=True), 'pipeline_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'python_version': FieldInfo(annotation=Union[str, NoneType], required=True), 'stack_checksum': FieldInfo(annotation=Union[str, NoneType], required=True), 'stack_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True), 'zenml_version': FieldInfo(annotation=Union[str, NoneType], required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### pipeline *: Mapped[[PipelineSchema](#zenml.zen_stores.schemas.PipelineSchema) | None]*

#### pipeline_id *: UUID | None*

#### python_version *: str | None*

#### stack *: Mapped[[StackSchema](#zenml.zen_stores.schemas.StackSchema) | None]*

#### stack_checksum *: str | None*

#### stack_id *: UUID | None*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [PipelineBuildResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_build.PipelineBuildResponse)

Convert a PipelineBuildSchema to a PipelineBuildResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created PipelineBuildResponse.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

#### zenml_version *: str | None*

### *class* zenml.zen_stores.schemas.PipelineDeploymentSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, pipeline_configuration: str, step_configurations: str, client_environment: str, run_name_template: str, client_version: str, server_version: str, pipeline_version_hash: str | None = None, pipeline_spec: str | None, code_path: str | None, user_id: UUID | None, workspace_id: UUID, stack_id: UUID | None, pipeline_id: UUID | None, schedule_id: UUID | None, build_id: UUID | None, code_reference_id: UUID | None, template_id: UUID | None = None)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

SQL Model for pipeline deployments.

#### build *: Mapped[[PipelineBuildSchema](#zenml.zen_stores.schemas.PipelineBuildSchema) | None]*

#### build_id *: UUID | None*

#### client_environment *: str*

#### client_version *: str*

#### code_path *: str | None*

#### code_reference *: Mapped[[CodeReferenceSchema](#zenml.zen_stores.schemas.CodeReferenceSchema) | None]*

#### code_reference_id *: UUID | None*

#### created *: datetime*

#### *classmethod* from_request(request: [PipelineDeploymentRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentRequest), code_reference_id: UUID | None) → [PipelineDeploymentSchema](#zenml.zen_stores.schemas.pipeline_deployment_schemas.PipelineDeploymentSchema)

Convert a PipelineDeploymentRequest to a PipelineDeploymentSchema.

Args:
: request: The request to convert.
  code_reference_id: Optional ID of the code reference for the
  <br/>
  > deployment.

Returns:
: The created PipelineDeploymentSchema.

#### id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'build_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'client_environment': FieldInfo(annotation=str, required=True), 'client_version': FieldInfo(annotation=str, required=True), 'code_path': FieldInfo(annotation=Union[str, NoneType], required=True), 'code_reference_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'pipeline_configuration': FieldInfo(annotation=str, required=True), 'pipeline_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'pipeline_spec': FieldInfo(annotation=Union[str, NoneType], required=True), 'pipeline_version_hash': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'run_name_template': FieldInfo(annotation=str, required=True), 'schedule_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'server_version': FieldInfo(annotation=str, required=True), 'stack_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'step_configurations': FieldInfo(annotation=str, required=True), 'template_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### pipeline *: Mapped[[PipelineSchema](#zenml.zen_stores.schemas.PipelineSchema) | None]*

#### pipeline_configuration *: str*

#### pipeline_id *: UUID | None*

#### pipeline_runs *: Mapped[List[[PipelineRunSchema](#zenml.zen_stores.schemas.PipelineRunSchema)]]*

#### pipeline_spec *: str | None*

#### pipeline_version_hash *: str | None*

#### run_name_template *: str*

#### schedule *: Mapped[[ScheduleSchema](#zenml.zen_stores.schemas.ScheduleSchema) | None]*

#### schedule_id *: UUID | None*

#### server_version *: str*

#### stack *: Mapped[[StackSchema](#zenml.zen_stores.schemas.StackSchema) | None]*

#### stack_id *: UUID | None*

#### step_configurations *: str*

#### step_runs *: Mapped[List[[StepRunSchema](#zenml.zen_stores.schemas.StepRunSchema)]]*

#### template_id *: UUID | None*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [PipelineDeploymentResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentResponse)

Convert a PipelineDeploymentSchema to a PipelineDeploymentResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created PipelineDeploymentResponse.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

### *class* zenml.zen_stores.schemas.PipelineRunSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, orchestrator_run_id: str | None, start_time: datetime | None, end_time: datetime | None = None, status: str, orchestrator_environment: str | None, deployment_id: UUID | None, user_id: UUID | None, workspace_id: UUID, pipeline_id: UUID | None, model_version_id: UUID, pipeline_configuration: str | None, client_environment: str | None, stack_id: UUID | None, build_id: UUID | None, schedule_id: UUID | None, trigger_execution_id: UUID | None)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for pipeline runs.

#### build *: Mapped[[PipelineBuildSchema](#zenml.zen_stores.schemas.PipelineBuildSchema) | None]*

#### build_id *: UUID | None*

#### client_environment *: str | None*

#### created *: datetime*

#### deployment *: Mapped[[PipelineDeploymentSchema](#zenml.zen_stores.schemas.PipelineDeploymentSchema) | None]*

#### deployment_id *: UUID | None*

#### end_time *: datetime | None*

#### *classmethod* from_request(request: [PipelineRunRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunRequest)) → [PipelineRunSchema](#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema)

Convert a PipelineRunRequest to a PipelineRunSchema.

Args:
: request: The request to convert.

Returns:
: The created PipelineRunSchema.

#### id *: UUID*

#### logs *: Mapped[[LogsSchema](#zenml.zen_stores.schemas.LogsSchema) | None]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'protected_namespaces': (), 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'build_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'client_environment': FieldInfo(annotation=Union[str, NoneType], required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'deployment_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'end_time': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'model_version_id': FieldInfo(annotation=UUID, required=True), 'name': FieldInfo(annotation=str, required=True), 'orchestrator_environment': FieldInfo(annotation=Union[str, NoneType], required=True), 'orchestrator_run_id': FieldInfo(annotation=Union[str, NoneType], required=True), 'pipeline_configuration': FieldInfo(annotation=Union[str, NoneType], required=True), 'pipeline_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'schedule_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'stack_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'start_time': FieldInfo(annotation=Union[datetime, NoneType], required=True), 'status': FieldInfo(annotation=str, required=True), 'trigger_execution_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_version *: Mapped[[ModelVersionSchema](#zenml.zen_stores.schemas.ModelVersionSchema)]*

#### model_version_id *: UUID*

#### model_versions_pipeline_runs_links *: Mapped[List[[ModelVersionPipelineRunSchema](#zenml.zen_stores.schemas.ModelVersionPipelineRunSchema)]]*

#### name *: str*

#### orchestrator_environment *: str | None*

#### orchestrator_run_id *: str | None*

#### pipeline *: Mapped[[PipelineSchema](#zenml.zen_stores.schemas.PipelineSchema) | None]*

#### pipeline_configuration *: str | None*

#### pipeline_id *: UUID | None*

#### run_metadata *: Mapped[List[[RunMetadataSchema](#zenml.zen_stores.schemas.RunMetadataSchema)]]*

#### schedule *: Mapped[[ScheduleSchema](#zenml.zen_stores.schemas.ScheduleSchema) | None]*

#### schedule_id *: UUID | None*

#### services *: Mapped[List[[ServiceSchema](#zenml.zen_stores.schemas.ServiceSchema)]]*

#### stack *: Mapped[[StackSchema](#zenml.zen_stores.schemas.StackSchema) | None]*

#### stack_id *: UUID | None*

#### start_time *: datetime | None*

#### status *: str*

#### step_runs *: Mapped[List[[StepRunSchema](#zenml.zen_stores.schemas.StepRunSchema)]]*

#### tags *: Mapped[List[[TagResourceSchema](#zenml.zen_stores.schemas.TagResourceSchema)]]*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse)

Convert a PipelineRunSchema to a PipelineRunResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created PipelineRunResponse.

Raises:
: RuntimeError: if the model creation fails.

#### trigger_execution *: Mapped[[TriggerExecutionSchema](#zenml.zen_stores.schemas.TriggerExecutionSchema) | None]*

#### trigger_execution_id *: UUID | None*

#### update(run_update: [PipelineRunUpdate](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunUpdate)) → [PipelineRunSchema](#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema)

Update a PipelineRunSchema with a PipelineRunUpdate.

Args:
: run_update: The PipelineRunUpdate to update with.

Returns:
: The updated PipelineRunSchema.

#### update_placeholder(request: [PipelineRunRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunRequest)) → [PipelineRunSchema](#zenml.zen_stores.schemas.pipeline_run_schemas.PipelineRunSchema)

Update a placeholder run.

Args:
: request: The pipeline run request which should replace the
  : placeholder.

Raises:
: RuntimeError: If the DB entry does not represent a placeholder run.
  ValueError: If the run request does not match the deployment or
  <br/>
  > pipeline ID of the placeholder run.

Returns:
: The updated PipelineRunSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

### *class* zenml.zen_stores.schemas.PipelineSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, description: str | None, workspace_id: UUID, user_id: UUID | None)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for pipelines.

#### builds *: Mapped[List[[PipelineBuildSchema](#zenml.zen_stores.schemas.PipelineBuildSchema)]]*

#### created *: datetime*

#### deployments *: Mapped[List[[PipelineDeploymentSchema](#zenml.zen_stores.schemas.PipelineDeploymentSchema)]]*

#### description *: str | None*

#### *classmethod* from_request(pipeline_request: [PipelineRequest](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineRequest)) → [PipelineSchema](#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema)

Convert a PipelineRequest to a PipelineSchema.

Args:
: pipeline_request: The request model to convert.

Returns:
: The converted schema.

#### id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'description': FieldInfo(annotation=Union[str, NoneType], required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'name': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### runs *: Mapped[List[[PipelineRunSchema](#zenml.zen_stores.schemas.PipelineRunSchema)]]*

#### schedules *: Mapped[List[[ScheduleSchema](#zenml.zen_stores.schemas.ScheduleSchema)]]*

#### tags *: Mapped[List[[TagResourceSchema](#zenml.zen_stores.schemas.TagResourceSchema)]]*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [PipelineResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineResponse)

Convert a PipelineSchema to a PipelineResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created PipelineResponse.

#### update(pipeline_update: [PipelineUpdate](zenml.models.v2.core.md#zenml.models.v2.core.pipeline.PipelineUpdate)) → [PipelineSchema](#zenml.zen_stores.schemas.pipeline_schemas.PipelineSchema)

Update a PipelineSchema with a PipelineUpdate.

Args:
: pipeline_update: The update model.

Returns:
: The updated PipelineSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

### *class* zenml.zen_stores.schemas.RunMetadataSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, resource_id: UUID, resource_type: str, stack_component_id: UUID | None, user_id: UUID | None, workspace_id: UUID, key: str, value: str, type: str)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

SQL Model for run metadata.

#### artifact_version *: Mapped[List[[ArtifactVersionSchema](#zenml.zen_stores.schemas.ArtifactVersionSchema)]]*

#### created *: datetime*

#### id *: UUID*

#### key *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'key': FieldInfo(annotation=str, required=True), 'resource_id': FieldInfo(annotation=UUID, required=True), 'resource_type': FieldInfo(annotation=str, required=True), 'stack_component_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'type': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'value': FieldInfo(annotation=str, required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_version *: Mapped[List[[ModelVersionSchema](#zenml.zen_stores.schemas.ModelVersionSchema)]]*

#### pipeline_run *: Mapped[List[[PipelineRunSchema](#zenml.zen_stores.schemas.PipelineRunSchema)]]*

#### resource_id *: UUID*

#### resource_type *: str*

#### stack_component *: Mapped[[StackComponentSchema](#zenml.zen_stores.schemas.StackComponentSchema) | None]*

#### stack_component_id *: UUID | None*

#### step_run *: Mapped[List[[StepRunSchema](#zenml.zen_stores.schemas.StepRunSchema)]]*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [RunMetadataResponse](zenml.models.v2.core.md#zenml.models.v2.core.run_metadata.RunMetadataResponse)

Convert a RunMetadataSchema to a RunMetadataResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created RunMetadataResponse.

#### type *: str*

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### value *: str*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

### *class* zenml.zen_stores.schemas.RunTemplateSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, description: str | None, user_id: UUID | None, workspace_id: UUID, source_deployment_id: UUID | None)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

SQL Model for run templates.

#### created *: datetime*

#### description *: str | None*

#### *classmethod* from_request(request: [RunTemplateRequest](zenml.models.v2.core.md#zenml.models.v2.core.run_template.RunTemplateRequest)) → [RunTemplateSchema](#zenml.zen_stores.schemas.run_template_schemas.RunTemplateSchema)

Create a schema from a request.

Args:
: request: The request to convert.

Returns:
: The created schema.

#### id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'description': FieldInfo(annotation=Union[str, NoneType], required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'name': FieldInfo(annotation=str, required=True), 'source_deployment_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### runs *: Mapped[List[[PipelineRunSchema](#zenml.zen_stores.schemas.PipelineRunSchema)]]*

#### source_deployment *: Mapped[[PipelineDeploymentSchema](#zenml.zen_stores.schemas.PipelineDeploymentSchema) | None]*

#### source_deployment_id *: UUID | None*

#### tags *: Mapped[List[[TagResourceSchema](#zenml.zen_stores.schemas.TagResourceSchema)]]*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [RunTemplateResponse](zenml.models.v2.core.md#zenml.models.v2.core.run_template.RunTemplateResponse)

Convert the schema to a response model.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: Model representing this schema.

#### update(update: [RunTemplateUpdate](zenml.models.v2.core.md#zenml.models.v2.core.run_template.RunTemplateUpdate)) → [RunTemplateSchema](#zenml.zen_stores.schemas.run_template_schemas.RunTemplateSchema)

Update the schema.

Args:
: update: The update model.

Returns:
: The updated schema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

### *class* zenml.zen_stores.schemas.ScheduleSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, workspace_id: UUID, user_id: UUID | None, pipeline_id: UUID | None, orchestrator_id: UUID | None, active: bool, cron_expression: str | None, start_time: datetime | None, end_time: datetime | None, interval_second: float | None, catchup: bool, run_once_start_time: datetime | None)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for schedules.

#### active *: bool*

#### catchup *: bool*

#### created *: datetime*

#### cron_expression *: str | None*

#### deployment *: Mapped[[PipelineDeploymentSchema](#zenml.zen_stores.schemas.PipelineDeploymentSchema) | None]*

#### end_time *: datetime | None*

#### *classmethod* from_request(schedule_request: [ScheduleRequest](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleRequest)) → [ScheduleSchema](#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema)

Create a ScheduleSchema from a ScheduleRequest.

Args:
: schedule_request: The ScheduleRequest to create the schema from.

Returns:
: The created ScheduleSchema.

#### id *: UUID*

#### interval_second *: float | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'active': FieldInfo(annotation=bool, required=True), 'catchup': FieldInfo(annotation=bool, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'cron_expression': FieldInfo(annotation=Union[str, NoneType], required=True), 'end_time': FieldInfo(annotation=Union[datetime, NoneType], required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'interval_second': FieldInfo(annotation=Union[float, NoneType], required=True), 'name': FieldInfo(annotation=str, required=True), 'orchestrator_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'pipeline_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'run_once_start_time': FieldInfo(annotation=Union[datetime, NoneType], required=True), 'start_time': FieldInfo(annotation=Union[datetime, NoneType], required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### orchestrator *: Mapped[[StackComponentSchema](#zenml.zen_stores.schemas.StackComponentSchema)]*

#### orchestrator_id *: UUID | None*

#### pipeline *: Mapped[[PipelineSchema](#zenml.zen_stores.schemas.PipelineSchema)]*

#### pipeline_id *: UUID | None*

#### run_once_start_time *: datetime | None*

#### start_time *: datetime | None*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [ScheduleResponse](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleResponse)

Convert a ScheduleSchema to a ScheduleResponseModel.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created ScheduleResponseModel.

#### update(schedule_update: [ScheduleUpdate](zenml.models.v2.core.md#zenml.models.v2.core.schedule.ScheduleUpdate)) → [ScheduleSchema](#zenml.zen_stores.schemas.schedule_schema.ScheduleSchema)

Update a ScheduleSchema from a ScheduleUpdateModel.

Args:
: schedule_update: The ScheduleUpdateModel to update the schema from.

Returns:
: The updated ScheduleSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

### *class* zenml.zen_stores.schemas.SecretSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, scope: str, values: bytes | None, workspace_id: UUID, user_id: UUID)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for secrets.

Attributes:
: name: The name of the secret.
  values: The values of the secret.

#### created *: datetime*

#### *classmethod* from_request(secret: [SecretRequest](zenml.models.v2.core.md#zenml.models.v2.core.secret.SecretRequest)) → [SecretSchema](#zenml.zen_stores.schemas.secret_schemas.SecretSchema)

Create a SecretSchema from a SecretRequest.

Args:
: secret: The SecretRequest from which to create the schema.

Returns:
: The created SecretSchema.

#### get_secret_values(encryption_engine: AesGcmEngine | None = None) → Dict[str, str]

Get the secret values for this secret.

This method is used by the SQL secrets store to load the secret values
from the database.

Args:
: encryption_engine: The encryption engine to use to decrypt the
  : secret values. If None, the values will be base64 decoded.

Returns:
: The secret values

Raises:
: KeyError: if no secret values for the given ID are stored in the
  : secrets store.

#### id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'name': FieldInfo(annotation=str, required=True), 'scope': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=UUID, required=True), 'values': FieldInfo(annotation=Union[bytes, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### scope *: str*

#### set_secret_values(secret_values: Dict[str, str], encryption_engine: AesGcmEngine | None = None) → None

Create a SecretSchema from a SecretRequest.

This method is used by the SQL secrets store to store the secret values
in the database.

Args:
: secret_values: The new secret values.
  encryption_engine: The encryption engine to use to encrypt the
  <br/>
  > secret values. If None, the values will be base64 encoded.

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [SecretResponse](zenml.models.v2.core.md#zenml.models.v2.core.secret.SecretResponse)

Converts a secret schema to a secret model.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The secret model.

#### update(secret_update: [SecretUpdate](zenml.models.v2.core.md#zenml.models.v2.core.secret.SecretUpdate)) → [SecretSchema](#zenml.zen_stores.schemas.secret_schemas.SecretSchema)

Update a SecretSchema from a SecretUpdate.

Args:
: secret_update: The SecretUpdate from which to update the schema.

Returns:
: The updated SecretSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.UserSchema)]*

#### user_id *: UUID*

#### values *: bytes | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

### *class* zenml.zen_stores.schemas.ServerSettingsSchema(\*, id: UUID, server_name: str, logo_url: str | None, active: bool = False, enable_analytics: bool = False, display_announcements: bool | None, display_updates: bool | None, onboarding_state: str | None, last_user_activity: datetime = None, updated: datetime = None)

Bases: `SQLModel`

SQL Model for the server settings.

#### active *: bool*

#### display_announcements *: bool | None*

#### display_updates *: bool | None*

#### enable_analytics *: bool*

#### id *: UUID*

#### last_user_activity *: datetime*

#### logo_url *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'active': FieldInfo(annotation=bool, required=False, default=False), 'display_announcements': FieldInfo(annotation=Union[bool, NoneType], required=True), 'display_updates': FieldInfo(annotation=Union[bool, NoneType], required=True), 'enable_analytics': FieldInfo(annotation=bool, required=False, default=False), 'id': FieldInfo(annotation=UUID, required=True), 'last_user_activity': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'logo_url': FieldInfo(annotation=Union[str, NoneType], required=True), 'onboarding_state': FieldInfo(annotation=Union[str, NoneType], required=True), 'server_name': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### onboarding_state *: str | None*

#### server_name *: str*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [ServerSettingsResponse](zenml.models.v2.core.md#zenml.models.v2.core.server_settings.ServerSettingsResponse)

Convert an ServerSettingsSchema to an ServerSettingsResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created SettingsResponse.

#### update(settings_update: [ServerSettingsUpdate](zenml.models.v2.core.md#zenml.models.v2.core.server_settings.ServerSettingsUpdate)) → [ServerSettingsSchema](#zenml.zen_stores.schemas.server_settings_schemas.ServerSettingsSchema)

Update a ServerSettingsSchema from a ServerSettingsUpdate.

Args:
: settings_update: The ServerSettingsUpdate from which
  : to update the schema.

Returns:
: The updated ServerSettingsSchema.

#### update_onboarding_state(completed_steps: Set[str]) → [ServerSettingsSchema](#zenml.zen_stores.schemas.server_settings_schemas.ServerSettingsSchema)

Update the onboarding state.

Args:
: completed_steps: Newly completed onboarding steps.

Returns:
: The updated schema.

#### updated *: datetime*

### *class* zenml.zen_stores.schemas.ServiceConnectorSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, connector_type: str, description: str, auth_method: str, resource_types: bytes, resource_id: str | None, supports_instances: bool, configuration: bytes | None, secret_id: UUID | None, expires_at: datetime | None, expires_skew_tolerance: int | None, expiration_seconds: int | None, labels: bytes | None, workspace_id: UUID, user_id: UUID | None)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for service connectors.

#### auth_method *: str*

#### components *: Mapped[List[[StackComponentSchema](#zenml.zen_stores.schemas.StackComponentSchema)]]*

#### configuration *: bytes | None*

#### connector_type *: str*

#### created *: datetime*

#### description *: str*

#### expiration_seconds *: int | None*

#### expires_at *: datetime | None*

#### expires_skew_tolerance *: int | None*

#### *classmethod* from_request(connector_request: [ServiceConnectorRequest](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorRequest), secret_id: UUID | None = None) → [ServiceConnectorSchema](#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema)

Create a ServiceConnectorSchema from a ServiceConnectorRequest.

Args:
: connector_request: The ServiceConnectorRequest from which to
  : create the schema.
  <br/>
  secret_id: The ID of the secret to use for this connector.

Returns:
: The created ServiceConnectorSchema.

#### has_labels(labels: Dict[str, str | None]) → bool

Checks if the connector has the given labels.

Args:
: labels: The labels to check for.

Returns:
: Whether the connector has the given labels.

#### id *: UUID*

#### labels *: bytes | None*

#### *property* labels_dict *: Dict[str, str]*

Returns the labels as a dictionary.

Returns:
: The labels as a dictionary.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'auth_method': FieldInfo(annotation=str, required=True), 'configuration': FieldInfo(annotation=Union[bytes, NoneType], required=True), 'connector_type': FieldInfo(annotation=str, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'description': FieldInfo(annotation=str, required=True), 'expiration_seconds': FieldInfo(annotation=Union[int, NoneType], required=True), 'expires_at': FieldInfo(annotation=Union[datetime, NoneType], required=True), 'expires_skew_tolerance': FieldInfo(annotation=Union[int, NoneType], required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'labels': FieldInfo(annotation=Union[bytes, NoneType], required=True), 'name': FieldInfo(annotation=str, required=True), 'resource_id': FieldInfo(annotation=Union[str, NoneType], required=True), 'resource_types': FieldInfo(annotation=bytes, required=True), 'secret_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'supports_instances': FieldInfo(annotation=bool, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### resource_id *: str | None*

#### resource_types *: bytes*

#### *property* resource_types_list *: List[str]*

Returns the resource types as a list.

Returns:
: The resource types as a list.

#### secret_id *: UUID | None*

#### supports_instances *: bool*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [ServiceConnectorResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorResponse)

Creates a ServiceConnector from a ServiceConnectorSchema.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: A ServiceConnectorModel

#### update(connector_update: [ServiceConnectorUpdate](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorUpdate), secret_id: UUID | None = None) → [ServiceConnectorSchema](#zenml.zen_stores.schemas.service_connector_schemas.ServiceConnectorSchema)

Updates a ServiceConnectorSchema from a ServiceConnectorUpdate.

Args:
: connector_update: The ServiceConnectorUpdate to update from.
  secret_id: The ID of the secret to use for this connector.

Returns:
: The updated ServiceConnectorSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

### *class* zenml.zen_stores.schemas.ServiceSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, workspace_id: UUID, user_id: UUID | None, service_source: str | None, service_type: str, type: str, flavor: str, admin_state: str | None, state: str | None, labels: bytes | None, config: bytes, status: bytes | None, endpoint: bytes | None, prediction_url: str | None, health_check_url: str | None, pipeline_name: str | None, pipeline_step_name: str | None, model_version_id: UUID | None, pipeline_run_id: UUID | None)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for service.

#### admin_state *: str | None*

#### config *: bytes*

#### created *: datetime*

#### endpoint *: bytes | None*

#### flavor *: str*

#### *classmethod* from_request(service_request: [ServiceRequest](zenml.models.v2.core.md#zenml.models.v2.core.service.ServiceRequest)) → [ServiceSchema](#zenml.zen_stores.schemas.service_schemas.ServiceSchema)

Convert a ServiceRequest to a ServiceSchema.

Args:
: service_request: The request model to convert.

Returns:
: The converted schema.

#### health_check_url *: str | None*

#### id *: UUID*

#### labels *: bytes | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'protected_namespaces': (), 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'admin_state': FieldInfo(annotation=Union[str, NoneType], required=True), 'config': FieldInfo(annotation=bytes, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'endpoint': FieldInfo(annotation=Union[bytes, NoneType], required=True), 'flavor': FieldInfo(annotation=str, required=True), 'health_check_url': FieldInfo(annotation=Union[str, NoneType], required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'labels': FieldInfo(annotation=Union[bytes, NoneType], required=True), 'model_version_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'name': FieldInfo(annotation=str, required=True), 'pipeline_name': FieldInfo(annotation=Union[str, NoneType], required=True), 'pipeline_run_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'pipeline_step_name': FieldInfo(annotation=Union[str, NoneType], required=True), 'prediction_url': FieldInfo(annotation=Union[str, NoneType], required=True), 'service_source': FieldInfo(annotation=Union[str, NoneType], required=True), 'service_type': FieldInfo(annotation=str, required=True), 'state': FieldInfo(annotation=Union[str, NoneType], required=True), 'status': FieldInfo(annotation=Union[bytes, NoneType], required=True), 'type': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_version *: Mapped[[ModelVersionSchema](#zenml.zen_stores.schemas.ModelVersionSchema) | None]*

#### model_version_id *: UUID | None*

#### name *: str*

#### pipeline_name *: str | None*

#### pipeline_run *: Mapped[[PipelineRunSchema](#zenml.zen_stores.schemas.PipelineRunSchema) | None]*

#### pipeline_run_id *: UUID | None*

#### pipeline_step_name *: str | None*

#### prediction_url *: str | None*

#### service_source *: str | None*

#### service_type *: str*

#### state *: str | None*

#### status *: bytes | None*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [ServiceResponse](zenml.models.v2.core.md#zenml.models.v2.core.service.ServiceResponse)

Convert an ServiceSchema to an ServiceResponse.

Args:
: include_metadata: Whether to include metadata in the response.
  include_resources: Whether to include resources in the response.
  kwargs: Additional keyword arguments.

Returns:
: The created ServiceResponse.

#### type *: str*

#### update(update: [ServiceUpdate](zenml.models.v2.core.md#zenml.models.v2.core.service.ServiceUpdate)) → [ServiceSchema](#zenml.zen_stores.schemas.service_schemas.ServiceSchema)

Updates a ServiceSchema from a ServiceUpdate.

Args:
: update: The ServiceUpdate to update from.

Returns:
: The updated ServiceSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

### *class* zenml.zen_stores.schemas.StackComponentSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, type: str, flavor: str, configuration: bytes, labels: bytes | None, component_spec_path: str | None, workspace_id: UUID, user_id: UUID | None, connector_id: UUID | None, connector_resource_id: str | None)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for stack components.

#### component_spec_path *: str | None*

#### configuration *: bytes*

#### connector *: Mapped[[ServiceConnectorSchema](#zenml.zen_stores.schemas.ServiceConnectorSchema) | None]*

#### connector_id *: UUID | None*

#### connector_resource_id *: str | None*

#### created *: datetime*

#### flavor *: str*

#### flavor_schema *: Mapped[[FlavorSchema](#zenml.zen_stores.schemas.FlavorSchema) | None]*

#### id *: UUID*

#### labels *: bytes | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'component_spec_path': FieldInfo(annotation=Union[str, NoneType], required=True), 'configuration': FieldInfo(annotation=bytes, required=True), 'connector_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'connector_resource_id': FieldInfo(annotation=Union[str, NoneType], required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'flavor': FieldInfo(annotation=str, required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'labels': FieldInfo(annotation=Union[bytes, NoneType], required=True), 'name': FieldInfo(annotation=str, required=True), 'type': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### run_metadata *: Mapped[List[[RunMetadataSchema](#zenml.zen_stores.schemas.RunMetadataSchema)]]*

#### run_or_step_logs *: Mapped[List[[LogsSchema](#zenml.zen_stores.schemas.LogsSchema)]]*

#### schedules *: Mapped[List[[ScheduleSchema](#zenml.zen_stores.schemas.ScheduleSchema)]]*

#### stacks *: Mapped[List[[StackSchema](#zenml.zen_stores.schemas.StackSchema)]]*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [ComponentResponse](zenml.models.v2.core.md#zenml.models.v2.core.component.ComponentResponse)

Creates a ComponentModel from an instance of a StackComponentSchema.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: A ComponentModel

#### type *: str*

#### update(component_update: [ComponentUpdate](zenml.models.v2.core.md#zenml.models.v2.core.component.ComponentUpdate)) → [StackComponentSchema](#zenml.zen_stores.schemas.component_schemas.StackComponentSchema)

Updates a StackComponentSchema from a ComponentUpdate.

Args:
: component_update: The ComponentUpdate to update from.

Returns:
: The updated StackComponentSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

### *class* zenml.zen_stores.schemas.StackCompositionSchema(\*, stack_id: UUID, component_id: UUID)

Bases: `SQLModel`

SQL Model for stack definitions.

Join table between Stacks and StackComponents.

#### component_id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'component_id': FieldInfo(annotation=UUID, required=True), 'stack_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### stack_id *: UUID*

### *class* zenml.zen_stores.schemas.StackSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, stack_spec_path: str | None, labels: bytes | None, workspace_id: UUID, user_id: UUID | None)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for stacks.

#### builds *: Mapped[List[[PipelineBuildSchema](#zenml.zen_stores.schemas.PipelineBuildSchema)]]*

#### components *: Mapped[List[[StackComponentSchema](#zenml.zen_stores.schemas.StackComponentSchema)]]*

#### created *: datetime*

#### deployments *: Mapped[List[[PipelineDeploymentSchema](#zenml.zen_stores.schemas.PipelineDeploymentSchema)]]*

#### id *: UUID*

#### labels *: bytes | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'labels': FieldInfo(annotation=Union[bytes, NoneType], required=True), 'name': FieldInfo(annotation=str, required=True), 'stack_spec_path': FieldInfo(annotation=Union[str, NoneType], required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### stack_spec_path *: str | None*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [StackResponse](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackResponse)

Converts the schema to a model.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The converted model.

#### update(stack_update: [StackUpdate](zenml.models.md#zenml.models.StackUpdate), components: List[[StackComponentSchema](#zenml.zen_stores.schemas.StackComponentSchema)]) → [StackSchema](#zenml.zen_stores.schemas.StackSchema)

Updates a stack schema with a stack update model.

Args:
: stack_update: StackUpdate to update the stack with.
  components: List of StackComponentSchema to update the stack with.

Returns:
: The updated StackSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

### *class* zenml.zen_stores.schemas.StepRunInputArtifactSchema(\*, name: str, type: str, step_id: UUID, artifact_id: UUID)

Bases: `SQLModel`

SQL Model that defines which artifacts are inputs to which step.

#### artifact_id *: UUID*

#### artifact_version *: Mapped[[ArtifactVersionSchema](#zenml.zen_stores.schemas.ArtifactVersionSchema)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact_id': FieldInfo(annotation=UUID, required=True), 'name': FieldInfo(annotation=str, required=True), 'step_id': FieldInfo(annotation=UUID, required=True), 'type': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### step_id *: UUID*

#### step_run *: Mapped[[StepRunSchema](#zenml.zen_stores.schemas.StepRunSchema)]*

#### type *: str*

### *class* zenml.zen_stores.schemas.StepRunOutputArtifactSchema(\*, name: str, type: str, step_id: UUID, artifact_id: UUID)

Bases: `SQLModel`

SQL Model that defines which artifacts are outputs of which step.

#### artifact_id *: UUID*

#### artifact_version *: Mapped[[ArtifactVersionSchema](#zenml.zen_stores.schemas.ArtifactVersionSchema)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact_id': FieldInfo(annotation=UUID, required=True), 'name': FieldInfo(annotation=str, required=True), 'step_id': FieldInfo(annotation=UUID, required=True), 'type': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### step_id *: UUID*

#### step_run *: Mapped[[StepRunSchema](#zenml.zen_stores.schemas.StepRunSchema)]*

#### type *: str*

### *class* zenml.zen_stores.schemas.StepRunParentsSchema(\*, parent_id: UUID, child_id: UUID)

Bases: `SQLModel`

SQL Model that defines the order of steps.

#### child_id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'child_id': FieldInfo(annotation=UUID, required=True), 'parent_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### parent_id *: UUID*

### *class* zenml.zen_stores.schemas.StepRunSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, start_time: datetime | None, end_time: datetime | None, status: str, docstring: str | None, cache_key: str | None, source_code: str | None, code_hash: str | None, step_configuration: str, original_step_run_id: UUID | None, deployment_id: UUID, pipeline_run_id: UUID, user_id: UUID | None, workspace_id: UUID, model_version_id: UUID)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for steps of pipeline runs.

#### cache_key *: str | None*

#### code_hash *: str | None*

#### created *: datetime*

#### deployment *: Mapped[[PipelineDeploymentSchema](#zenml.zen_stores.schemas.PipelineDeploymentSchema) | None]*

#### deployment_id *: UUID*

#### docstring *: str | None*

#### end_time *: datetime | None*

#### *classmethod* from_request(request: [StepRunRequest](zenml.models.v2.core.md#zenml.models.v2.core.step_run.StepRunRequest)) → [StepRunSchema](#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema)

Create a step run schema from a step run request model.

Args:
: request: The step run request model.

Returns:
: The step run schema.

#### id *: UUID*

#### input_artifacts *: Mapped[List[[StepRunInputArtifactSchema](#zenml.zen_stores.schemas.StepRunInputArtifactSchema)]]*

#### logs *: Mapped[[LogsSchema](#zenml.zen_stores.schemas.LogsSchema) | None]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'protected_namespaces': (), 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'cache_key': FieldInfo(annotation=Union[str, NoneType], required=True), 'code_hash': FieldInfo(annotation=Union[str, NoneType], required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'deployment_id': FieldInfo(annotation=UUID, required=True), 'docstring': FieldInfo(annotation=Union[str, NoneType], required=True), 'end_time': FieldInfo(annotation=Union[datetime, NoneType], required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'model_version_id': FieldInfo(annotation=UUID, required=True), 'name': FieldInfo(annotation=str, required=True), 'original_step_run_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'pipeline_run_id': FieldInfo(annotation=UUID, required=True), 'source_code': FieldInfo(annotation=Union[str, NoneType], required=True), 'start_time': FieldInfo(annotation=Union[datetime, NoneType], required=True), 'status': FieldInfo(annotation=str, required=True), 'step_configuration': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_version *: Mapped[[ModelVersionSchema](#zenml.zen_stores.schemas.ModelVersionSchema)]*

#### model_version_id *: UUID*

#### name *: str*

#### original_step_run_id *: UUID | None*

#### output_artifacts *: Mapped[List[[StepRunOutputArtifactSchema](#zenml.zen_stores.schemas.StepRunOutputArtifactSchema)]]*

#### parents *: Mapped[List[[StepRunParentsSchema](#zenml.zen_stores.schemas.StepRunParentsSchema)]]*

#### pipeline_run_id *: UUID*

#### run_metadata *: Mapped[List[[RunMetadataSchema](#zenml.zen_stores.schemas.RunMetadataSchema)]]*

#### source_code *: str | None*

#### start_time *: datetime | None*

#### status *: str*

#### step_configuration *: str*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [StepRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.step_run.StepRunResponse)

Convert a StepRunSchema to a StepRunResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created StepRunResponse.

Raises:
: ValueError: In case the step run configuration can not be loaded.
  RuntimeError: If the step run schema does not have a deployment_id
  <br/>
  > or a step_configuration.

#### update(step_update: [StepRunUpdate](zenml.models.v2.core.md#zenml.models.v2.core.step_run.StepRunUpdate)) → [StepRunSchema](#zenml.zen_stores.schemas.step_run_schemas.StepRunSchema)

Update a step run schema with a step run update model.

Args:
: step_update: The step run update model.

Returns:
: The updated step run schema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

### *class* zenml.zen_stores.schemas.TagResourceSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, tag_id: UUID, resource_id: UUID, resource_type: str)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

SQL Model for tag resource relationship.

#### artifact *: Mapped[List[[ArtifactSchema](#zenml.zen_stores.schemas.ArtifactSchema)]]*

#### artifact_version *: Mapped[List[[ArtifactVersionSchema](#zenml.zen_stores.schemas.ArtifactVersionSchema)]]*

#### created *: datetime*

#### *classmethod* from_request(request: [TagResourceRequest](zenml.models.v2.core.md#zenml.models.v2.core.tag_resource.TagResourceRequest)) → [TagResourceSchema](#zenml.zen_stores.schemas.tag_schemas.TagResourceSchema)

Convert an TagResourceRequest to an TagResourceSchema.

Args:
: request: The request model version to convert.

Returns:
: The converted schema.

#### id *: UUID*

#### model *: Mapped[List[[ModelSchema](#zenml.zen_stores.schemas.ModelSchema)]]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'resource_id': FieldInfo(annotation=UUID, required=True), 'resource_type': FieldInfo(annotation=str, required=True), 'tag_id': FieldInfo(annotation=UUID, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_version *: Mapped[List[[ModelVersionSchema](#zenml.zen_stores.schemas.ModelVersionSchema)]]*

#### resource_id *: UUID*

#### resource_type *: str*

#### tag *: Mapped[[TagSchema](#zenml.zen_stores.schemas.TagSchema)]*

#### tag_id *: UUID*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [TagResourceResponse](zenml.models.v2.core.md#zenml.models.v2.core.tag_resource.TagResourceResponse)

Convert an TagResourceSchema to an TagResourceResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created TagResourceResponse.

#### updated *: datetime*

### *class* zenml.zen_stores.schemas.TagSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, color: str)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for tag.

#### color *: str*

#### created *: datetime*

#### *classmethod* from_request(request: [TagRequest](zenml.models.v2.core.md#zenml.models.v2.core.tag.TagRequest)) → [TagSchema](#zenml.zen_stores.schemas.tag_schemas.TagSchema)

Convert an TagRequest to an TagSchema.

Args:
: request: The request model to convert.

Returns:
: The converted schema.

#### id *: UUID*

#### links *: Mapped[List[[TagResourceSchema](#zenml.zen_stores.schemas.TagResourceSchema)]]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'color': FieldInfo(annotation=str, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'name': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [TagResponse](zenml.models.v2.core.md#zenml.models.v2.core.tag.TagResponse)

Convert an TagSchema to an TagResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The created TagResponse.

#### update(update: [TagUpdate](zenml.models.v2.core.md#zenml.models.v2.core.tag.TagUpdate)) → [TagSchema](#zenml.zen_stores.schemas.tag_schemas.TagSchema)

Updates a TagSchema from a TagUpdate.

Args:
: update: The TagUpdate to update from.

Returns:
: The updated TagSchema.

#### updated *: datetime*

### *class* zenml.zen_stores.schemas.TriggerExecutionSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, trigger_id: UUID, event_metadata: bytes | None = None)

Bases: [`BaseSchema`](#zenml.zen_stores.schemas.base_schemas.BaseSchema)

SQL Model for trigger executions.

#### created *: datetime*

#### event_metadata *: bytes | None*

#### *classmethod* from_request(request: [TriggerExecutionRequest](zenml.models.v2.core.md#zenml.models.v2.core.trigger_execution.TriggerExecutionRequest)) → [TriggerExecutionSchema](#zenml.zen_stores.schemas.trigger_schemas.TriggerExecutionSchema)

Convert a TriggerExecutionRequest to a TriggerExecutionSchema.

Args:
: request: The request model to convert.

Returns:
: The converted schema.

#### id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'event_metadata': FieldInfo(annotation=Union[bytes, NoneType], required=False, default=None), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'trigger_id': FieldInfo(annotation=UUID, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [TriggerExecutionResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger_execution.TriggerExecutionResponse)

Converts the schema to a model.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The converted model.

#### trigger *: Mapped[[TriggerSchema](#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema)]*

#### trigger_id *: UUID*

#### updated *: datetime*

### *class* zenml.zen_stores.schemas.TriggerSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, workspace_id: UUID, user_id: UUID | None, event_source_id: UUID | None, action_id: UUID, event_filter: bytes, schedule: bytes | None, description: str, is_active: bool)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for triggers.

#### action *: Mapped[[ActionSchema](#zenml.zen_stores.schemas.ActionSchema)]*

#### action_id *: UUID*

#### created *: datetime*

#### description *: str*

#### event_filter *: bytes*

#### event_source *: Mapped[[EventSourceSchema](#zenml.zen_stores.schemas.EventSourceSchema) | None]*

#### event_source_id *: UUID | None*

#### executions *: Mapped[List[[TriggerExecutionSchema](#zenml.zen_stores.schemas.TriggerExecutionSchema)]]*

#### *classmethod* from_request(request: [TriggerRequest](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerRequest)) → [TriggerSchema](#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema)

Convert a TriggerRequest to a TriggerSchema.

Args:
: request: The request model to convert.

Returns:
: The converted schema.

#### id *: UUID*

#### is_active *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'action_id': FieldInfo(annotation=UUID, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'description': FieldInfo(annotation=str, required=True), 'event_filter': FieldInfo(annotation=bytes, required=True), 'event_source_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'is_active': FieldInfo(annotation=bool, required=True), 'name': FieldInfo(annotation=str, required=True), 'schedule': FieldInfo(annotation=Union[bytes, NoneType], required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### schedule *: bytes | None*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [TriggerResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerResponse)

Converts the schema to a model.

Args:
: include_metadata: Flag deciding whether to include the output model(s)
  : metadata fields in the response.
  <br/>
  include_resources: Flag deciding whether to include the output model(s)
  : metadata fields in the response.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The converted model.

#### update(trigger_update: [TriggerUpdate](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerUpdate)) → [TriggerSchema](#zenml.zen_stores.schemas.trigger_schemas.TriggerSchema)

Updates a trigger schema with a trigger update model.

Args:
: trigger_update: TriggerUpdate to update the trigger with.

Returns:
: The updated TriggerSchema.

#### updated *: datetime*

#### user *: Mapped[[UserSchema](#zenml.zen_stores.schemas.UserSchema) | None]*

#### user_id *: UUID | None*

#### workspace *: Mapped[[WorkspaceSchema](#zenml.zen_stores.schemas.WorkspaceSchema)]*

#### workspace_id *: UUID*

### *class* zenml.zen_stores.schemas.UserSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, is_service_account: bool = False, full_name: str, description: str | None, email: str | None, active: bool, password: str | None, activation_token: str | None, email_opted_in: bool | None, external_user_id: UUID | None, is_admin: bool = False, user_metadata: str | None)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for users.

#### actions *: Mapped[List[[ActionSchema](#zenml.zen_stores.schemas.ActionSchema)]]*

#### activation_token *: str | None*

#### active *: bool*

#### api_keys *: Mapped[List[[APIKeySchema](#zenml.zen_stores.schemas.APIKeySchema)]]*

#### artifact_versions *: Mapped[List[[ArtifactVersionSchema](#zenml.zen_stores.schemas.ArtifactVersionSchema)]]*

#### auth_actions *: Mapped[List[[ActionSchema](#zenml.zen_stores.schemas.ActionSchema)]]*

#### auth_devices *: Mapped[List[[OAuthDeviceSchema](#zenml.zen_stores.schemas.OAuthDeviceSchema)]]*

#### builds *: Mapped[List[[PipelineBuildSchema](#zenml.zen_stores.schemas.PipelineBuildSchema)]]*

#### code_repositories *: Mapped[List[[CodeRepositorySchema](#zenml.zen_stores.schemas.CodeRepositorySchema)]]*

#### components *: Mapped[List[[StackComponentSchema](#zenml.zen_stores.schemas.StackComponentSchema)]]*

#### created *: datetime*

#### deployments *: Mapped[List[[PipelineDeploymentSchema](#zenml.zen_stores.schemas.PipelineDeploymentSchema)]]*

#### description *: str | None*

#### email *: str | None*

#### email_opted_in *: bool | None*

#### event_sources *: Mapped[List[[EventSourceSchema](#zenml.zen_stores.schemas.EventSourceSchema)]]*

#### external_user_id *: UUID | None*

#### flavors *: Mapped[List[[FlavorSchema](#zenml.zen_stores.schemas.FlavorSchema)]]*

#### *classmethod* from_service_account_request(model: [ServiceAccountRequest](zenml.models.v2.core.md#zenml.models.v2.core.service_account.ServiceAccountRequest)) → [UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema)

Create a UserSchema from a Service Account request.

Args:
: model: The ServiceAccountRequest from which to create the
  : schema.

Returns:
: The created UserSchema.

#### *classmethod* from_user_request(model: [UserRequest](zenml.models.v2.core.md#zenml.models.v2.core.user.UserRequest)) → [UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema)

Create a UserSchema from a UserRequest.

Args:
: model: The UserRequest from which to create the schema.

Returns:
: The created UserSchema.

#### full_name *: str*

#### id *: UUID*

#### is_admin *: bool*

#### is_service_account *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'activation_token': FieldInfo(annotation=Union[str, NoneType], required=True), 'active': FieldInfo(annotation=bool, required=True), 'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'description': FieldInfo(annotation=Union[str, NoneType], required=True), 'email': FieldInfo(annotation=Union[str, NoneType], required=True), 'email_opted_in': FieldInfo(annotation=Union[bool, NoneType], required=True), 'external_user_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'full_name': FieldInfo(annotation=str, required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'is_admin': FieldInfo(annotation=bool, required=False, default=False), 'is_service_account': FieldInfo(annotation=bool, required=False, default=False), 'name': FieldInfo(annotation=str, required=True), 'password': FieldInfo(annotation=Union[str, NoneType], required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'user_metadata': FieldInfo(annotation=Union[str, NoneType], required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_versions *: Mapped[List[[ModelVersionSchema](#zenml.zen_stores.schemas.ModelVersionSchema)]]*

#### model_versions_artifacts_links *: Mapped[List[[ModelVersionArtifactSchema](#zenml.zen_stores.schemas.ModelVersionArtifactSchema)]]*

#### model_versions_pipeline_runs_links *: Mapped[List[[ModelVersionPipelineRunSchema](#zenml.zen_stores.schemas.ModelVersionPipelineRunSchema)]]*

#### models *: Mapped[List[[ModelSchema](#zenml.zen_stores.schemas.ModelSchema)]]*

#### name *: str*

#### password *: str | None*

#### pipelines *: Mapped[List[[PipelineSchema](#zenml.zen_stores.schemas.PipelineSchema)]]*

#### run_metadata *: Mapped[List[[RunMetadataSchema](#zenml.zen_stores.schemas.RunMetadataSchema)]]*

#### runs *: Mapped[List[[PipelineRunSchema](#zenml.zen_stores.schemas.PipelineRunSchema)]]*

#### schedules *: Mapped[List[[ScheduleSchema](#zenml.zen_stores.schemas.ScheduleSchema)]]*

#### secrets *: Mapped[List[[SecretSchema](#zenml.zen_stores.schemas.SecretSchema)]]*

#### service_connectors *: Mapped[List[[ServiceConnectorSchema](#zenml.zen_stores.schemas.ServiceConnectorSchema)]]*

#### services *: Mapped[List[[ServiceSchema](#zenml.zen_stores.schemas.ServiceSchema)]]*

#### stacks *: Mapped[List[[StackSchema](#zenml.zen_stores.schemas.StackSchema)]]*

#### step_runs *: Mapped[List[[StepRunSchema](#zenml.zen_stores.schemas.StepRunSchema)]]*

#### to_model(include_metadata: bool = False, include_resources: bool = False, include_private: bool = False, \*\*kwargs: Any) → [UserResponse](zenml.models.v2.core.md#zenml.models.v2.core.user.UserResponse)

Convert a UserSchema to a UserResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic
  include_private: Whether to include the user private information
  <br/>
  > this is to limit the amount of data one can get
  > about other users

Returns:
: The converted UserResponse.

#### to_service_account_model(include_metadata: bool = False, include_resources: bool = False) → [ServiceAccountResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_account.ServiceAccountResponse)

Convert a UserSchema to a ServiceAccountResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.

Returns:
: The converted ServiceAccountResponse.

#### triggers *: Mapped[List[[TriggerSchema](#zenml.zen_stores.schemas.TriggerSchema)]]*

#### update_service_account(service_account_update: [ServiceAccountUpdate](zenml.models.v2.core.md#zenml.models.v2.core.service_account.ServiceAccountUpdate)) → [UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema)

Update a UserSchema from a ServiceAccountUpdate.

Args:
: service_account_update: The ServiceAccountUpdate from which
  : to update the schema.

Returns:
: The updated UserSchema.

#### update_user(user_update: [UserUpdate](zenml.models.v2.core.md#zenml.models.v2.core.user.UserUpdate)) → [UserSchema](#zenml.zen_stores.schemas.user_schemas.UserSchema)

Update a UserSchema from a UserUpdate.

Args:
: user_update: The UserUpdate from which to update the schema.

Returns:
: The updated UserSchema.

#### updated *: datetime*

#### user_metadata *: str | None*

### *class* zenml.zen_stores.schemas.WorkspaceSchema(\*, id: UUID = None, created: datetime = None, updated: datetime = None, name: str, description: str)

Bases: [`NamedSchema`](#zenml.zen_stores.schemas.base_schemas.NamedSchema)

SQL Model for workspaces.

#### actions *: Mapped[List[[ActionSchema](#zenml.zen_stores.schemas.ActionSchema)]]*

#### artifact_versions *: Mapped[List[[ArtifactVersionSchema](#zenml.zen_stores.schemas.ArtifactVersionSchema)]]*

#### builds *: Mapped[List[[PipelineBuildSchema](#zenml.zen_stores.schemas.PipelineBuildSchema)]]*

#### code_repositories *: Mapped[List[[CodeRepositorySchema](#zenml.zen_stores.schemas.CodeRepositorySchema)]]*

#### components *: Mapped[List[[StackComponentSchema](#zenml.zen_stores.schemas.StackComponentSchema)]]*

#### created *: datetime*

#### deployments *: Mapped[List[[PipelineDeploymentSchema](#zenml.zen_stores.schemas.PipelineDeploymentSchema)]]*

#### description *: str*

#### event_sources *: Mapped[List[[EventSourceSchema](#zenml.zen_stores.schemas.EventSourceSchema)]]*

#### flavors *: Mapped[List[[FlavorSchema](#zenml.zen_stores.schemas.FlavorSchema)]]*

#### *classmethod* from_request(workspace: [WorkspaceRequest](zenml.models.v2.core.md#zenml.models.v2.core.workspace.WorkspaceRequest)) → [WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)

Create a WorkspaceSchema from a WorkspaceResponse.

Args:
: workspace: The WorkspaceResponse from which to create the schema.

Returns:
: The created WorkspaceSchema.

#### id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'from_attributes': True, 'read_from_attributes': True, 'read_with_orm_mode': True, 'registry': PydanticUndefined, 'table': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method), 'description': FieldInfo(annotation=str, required=True), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4), 'name': FieldInfo(annotation=str, required=True), 'updated': FieldInfo(annotation=datetime, required=False, default_factory=builtin_function_or_method)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_versions *: Mapped[List[[ModelVersionSchema](#zenml.zen_stores.schemas.ModelVersionSchema)]]*

#### model_versions_artifacts_links *: Mapped[List[[ModelVersionArtifactSchema](#zenml.zen_stores.schemas.ModelVersionArtifactSchema)]]*

#### model_versions_pipeline_runs_links *: Mapped[List[[ModelVersionPipelineRunSchema](#zenml.zen_stores.schemas.ModelVersionPipelineRunSchema)]]*

#### models *: Mapped[List[[ModelSchema](#zenml.zen_stores.schemas.ModelSchema)]]*

#### name *: str*

#### pipelines *: Mapped[List[[PipelineSchema](#zenml.zen_stores.schemas.PipelineSchema)]]*

#### run_metadata *: Mapped[List[[RunMetadataSchema](#zenml.zen_stores.schemas.RunMetadataSchema)]]*

#### runs *: Mapped[List[[PipelineRunSchema](#zenml.zen_stores.schemas.PipelineRunSchema)]]*

#### schedules *: Mapped[List[[ScheduleSchema](#zenml.zen_stores.schemas.ScheduleSchema)]]*

#### secrets *: Mapped[List[[SecretSchema](#zenml.zen_stores.schemas.SecretSchema)]]*

#### service_connectors *: Mapped[List[[ServiceConnectorSchema](#zenml.zen_stores.schemas.ServiceConnectorSchema)]]*

#### services *: Mapped[List[[ServiceSchema](#zenml.zen_stores.schemas.ServiceSchema)]]*

#### stacks *: Mapped[List[[StackSchema](#zenml.zen_stores.schemas.StackSchema)]]*

#### step_runs *: Mapped[List[[StepRunSchema](#zenml.zen_stores.schemas.StepRunSchema)]]*

#### to_model(include_metadata: bool = False, include_resources: bool = False, \*\*kwargs: Any) → [WorkspaceResponse](zenml.models.v2.core.md#zenml.models.v2.core.workspace.WorkspaceResponse)

Convert a WorkspaceSchema to a WorkspaceResponse.

Args:
: include_metadata: Whether the metadata will be filled.
  include_resources: Whether the resources will be filled.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments to allow schema specific logic

Returns:
: The converted WorkspaceResponseModel.

#### triggers *: Mapped[List[[TriggerSchema](#zenml.zen_stores.schemas.TriggerSchema)]]*

#### update(workspace_update: [WorkspaceUpdate](zenml.models.v2.core.md#zenml.models.v2.core.workspace.WorkspaceUpdate)) → [WorkspaceSchema](#zenml.zen_stores.schemas.workspace_schemas.WorkspaceSchema)

Update a WorkspaceSchema from a WorkspaceUpdate.

Args:
: workspace_update: The WorkspaceUpdate from which to update the
  : schema.

Returns:
: The updated WorkspaceSchema.

#### updated *: datetime*
