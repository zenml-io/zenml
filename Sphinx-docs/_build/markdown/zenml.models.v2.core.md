# zenml.models.v2.core package

## Submodules

## zenml.models.v2.core.action module

Collection of all models concerning actions.

### *class* zenml.models.v2.core.action.ActionFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None, name: str | None = None, flavor: str | None = None, plugin_subtype: str | None = None)

Bases: [`WorkspaceScopedFilter`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedFilter)

Model to enable advanced filtering of all actions.

#### created *: datetime | str | None*

#### flavor *: str | None*

#### id *: UUID | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'flavor': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The flavor of the action.'), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Name of the action.'), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'plugin_subtype': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The subtype of the action.'), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str | None*

#### page *: int*

#### plugin_subtype *: str | None*

#### scope_workspace *: UUID | None*

#### size *: int*

#### sort_by *: str*

#### updated *: datetime | str | None*

### *class* zenml.models.v2.core.action.ActionRequest(\*, user: UUID, workspace: UUID, name: Annotated[str, MaxLen(max_length=255)], description: Annotated[str, MaxLen(max_length=255)] = '', flavor: Annotated[str, MaxLen(max_length=255)], plugin_subtype: Annotated[[PluginSubType](zenml.md#zenml.enums.PluginSubType), MaxLen(max_length=255)], configuration: Dict[str, Any], service_account_id: UUID, auth_window: int | None = None)

Bases: [`WorkspaceScopedRequest`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedRequest)

Model for creating a new action.

#### auth_window *: int | None*

#### configuration *: Dict[str, Any]*

#### description *: str*

#### flavor *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'auth_window': FieldInfo(annotation=Union[int, NoneType], required=False, default=None, title='The time window in minutes for which the service account is authorized to execute the action. Set this to 0 to authorize the service account indefinitely (not recommended). If not set, a default value defined for each individual action type is used.'), 'configuration': FieldInfo(annotation=Dict[str, Any], required=True, title='The configuration for the action.'), 'description': FieldInfo(annotation=str, required=False, default='', title='The description of the action', metadata=[MaxLen(max_length=255)]), 'flavor': FieldInfo(annotation=str, required=True, title='The flavor of the action.', metadata=[MaxLen(max_length=255)]), 'name': FieldInfo(annotation=str, required=True, title='The name of the action.', metadata=[MaxLen(max_length=255)]), 'plugin_subtype': FieldInfo(annotation=PluginSubType, required=True, title='The subtype of the action.', metadata=[MaxLen(max_length=255)]), 'service_account_id': FieldInfo(annotation=UUID, required=True, title='The service account that is used to execute the action.'), 'user': FieldInfo(annotation=UUID, required=True, title='The id of the user that created this resource.'), 'workspace': FieldInfo(annotation=UUID, required=True, title='The workspace to which this resource belongs.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### plugin_subtype *: [PluginSubType](zenml.md#zenml.enums.PluginSubType)*

#### service_account_id *: UUID*

#### user *: UUID*

#### workspace *: UUID*

### *class* zenml.models.v2.core.action.ActionResponse(\*, body: [ActionResponseBody](#zenml.models.v2.core.action.ActionResponseBody) | None = None, metadata: [ActionResponseMetadata](#zenml.models.v2.core.action.ActionResponseMetadata) | None = None, resources: [ActionResponseResources](#zenml.models.v2.core.action.ActionResponseResources) | None = None, id: UUID, permission_denied: bool = False, name: Annotated[str, MaxLen(max_length=255)])

Bases: `WorkspaceScopedResponse[ActionResponseBody, ActionResponseMetadata, ActionResponseResources]`

Response model for actions.

#### *property* auth_window *: int*

The auth_window property.

Returns:
: the value of the property.

#### body *: 'AnyBody' | None*

#### *property* configuration *: Dict[str, Any]*

The configuration property.

Returns:
: the value of the property.

#### *property* description *: str*

The description property.

Returns:
: the value of the property.

#### *property* flavor *: str*

The flavor property.

Returns:
: the value of the property.

#### get_hydrated_version() → [ActionResponse](#zenml.models.v2.core.action.ActionResponse)

Get the hydrated version of this action.

Returns:
: An instance of the same entity with the metadata field attached.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[ActionResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[ActionResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the action.', metadata=[MaxLen(max_length=255)]), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[ActionResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str*

#### permission_denied *: bool*

#### *property* plugin_subtype *: [PluginSubType](zenml.md#zenml.enums.PluginSubType)*

The plugin_subtype property.

Returns:
: the value of the property.

#### resources *: 'AnyResources' | None*

#### *property* service_account *: [UserResponse](#zenml.models.v2.core.user.UserResponse)*

The service_account property.

Returns:
: the value of the property.

#### set_configuration(configuration: Dict[str, Any]) → None

Set the configuration property.

Args:
: configuration: The value to set.

### *class* zenml.models.v2.core.action.ActionResponseBody(\*, created: datetime, updated: datetime, user: [UserResponse](#zenml.models.v2.core.user.UserResponse) | None = None, flavor: Annotated[str, MaxLen(max_length=255)], plugin_subtype: Annotated[[PluginSubType](zenml.md#zenml.enums.PluginSubType), MaxLen(max_length=255)])

Bases: [`WorkspaceScopedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseBody)

Response body for actions.

#### created *: datetime*

#### flavor *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'flavor': FieldInfo(annotation=str, required=True, title='The flavor of the action.', metadata=[MaxLen(max_length=255)]), 'plugin_subtype': FieldInfo(annotation=PluginSubType, required=True, title='The subtype of the action.', metadata=[MaxLen(max_length=255)]), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.'), 'user': FieldInfo(annotation=Union[UserResponse, NoneType], required=False, default=None, title='The user who created this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### plugin_subtype *: [PluginSubType](zenml.md#zenml.enums.PluginSubType)*

#### updated *: datetime*

#### user *: 'UserResponse' | None*

### *class* zenml.models.v2.core.action.ActionResponseMetadata(\*, workspace: [WorkspaceResponse](#zenml.models.v2.core.workspace.WorkspaceResponse), description: Annotated[str, MaxLen(max_length=255)] = '', configuration: Dict[str, Any], auth_window: int)

Bases: [`WorkspaceScopedResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseMetadata)

Response metadata for actions.

#### auth_window *: int*

#### configuration *: Dict[str, Any]*

#### description *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'auth_window': FieldInfo(annotation=int, required=True, title='The time window in minutes for which the service account is authorized to execute the action.'), 'configuration': FieldInfo(annotation=Dict[str, Any], required=True, title='The configuration for the action.'), 'description': FieldInfo(annotation=str, required=False, default='', title='The description of the action.', metadata=[MaxLen(max_length=255)]), 'workspace': FieldInfo(annotation=WorkspaceResponse, required=True, title='The workspace of this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

### *class* zenml.models.v2.core.action.ActionResponseResources(\*, service_account: [UserResponse](#zenml.models.v2.core.user.UserResponse), \*\*extra_data: Any)

Bases: [`WorkspaceScopedResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseResources)

Class for all resource models associated with the action entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'service_account': FieldInfo(annotation=UserResponse, required=True, title='The service account that is used to execute the action.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### service_account *: [UserResponse](#zenml.models.v2.core.user.UserResponse)*

### *class* zenml.models.v2.core.action.ActionUpdate(\*, name: Annotated[str | None, MaxLen(max_length=255)] = None, description: Annotated[str | None, MaxLen(max_length=255)] = None, configuration: Dict[str, Any] | None = None, service_account_id: UUID | None = None, auth_window: int | None = None)

Bases: [`BaseUpdate`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseUpdate)

Update model for actions.

#### auth_window *: int | None*

#### configuration *: Dict[str, Any] | None*

#### description *: str | None*

#### *classmethod* from_response(response: [ActionResponse](#zenml.models.v2.core.action.ActionResponse)) → [ActionUpdate](#zenml.models.v2.core.action.ActionUpdate)

Create an update model from a response model.

Args:
: response: The response model to create the update model from.

Returns:
: The update model.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'auth_window': FieldInfo(annotation=Union[int, NoneType], required=False, default=None, title='The time window in minutes for which the service account is authorized to execute the action. Set this to 0 to authorize the service account indefinitely (not recommended). If not set, a default value defined for each individual action type is used.'), 'configuration': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, title='The configuration for the action.'), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The new description for the action.', metadata=[MaxLen(max_length=255)]), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The new name for the action.', metadata=[MaxLen(max_length=255)]), 'service_account_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The service account that is used to execute the action.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

#### service_account_id *: UUID | None*

## zenml.models.v2.core.action_flavor module

Action flavor model definitions.

### *class* zenml.models.v2.core.action_flavor.ActionFlavorResponse(\*, body: [ActionFlavorResponseBody](#zenml.models.v2.core.action_flavor.ActionFlavorResponseBody) | None = None, metadata: [ActionFlavorResponseMetadata](#zenml.models.v2.core.action_flavor.ActionFlavorResponseMetadata) | None = None, resources: [ActionFlavorResponseResources](#zenml.models.v2.core.action_flavor.ActionFlavorResponseResources) | None = None, name: str, type: [PluginType](zenml.md#zenml.enums.PluginType), subtype: [PluginSubType](zenml.md#zenml.enums.PluginSubType))

Bases: `BasePluginFlavorResponse[ActionFlavorResponseBody, ActionFlavorResponseMetadata, ActionFlavorResponseResources]`

Response model for Action Flavors.

#### body *: 'AnyBody' | None*

#### *property* config_schema *: Dict[str, Any]*

The source_config_schema property.

Returns:
: the value of the property.

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[ActionFlavorResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'metadata': FieldInfo(annotation=Union[ActionFlavorResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='Name of the flavor.'), 'resources': FieldInfo(annotation=Union[ActionFlavorResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.'), 'subtype': FieldInfo(annotation=PluginSubType, required=True, title='Subtype of the plugin.'), 'type': FieldInfo(annotation=PluginType, required=True, title='Type of the plugin.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str*

#### resources *: 'AnyResources' | None*

#### subtype *: [PluginSubType](zenml.md#zenml.enums.PluginSubType)*

#### type *: [PluginType](zenml.md#zenml.enums.PluginType)*

### *class* zenml.models.v2.core.action_flavor.ActionFlavorResponseBody

Bases: [`BasePluginResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.base_plugin_flavor.BasePluginResponseBody)

Response body for action flavors.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.action_flavor.ActionFlavorResponseMetadata(\*, config_schema: Dict[str, Any])

Bases: [`BasePluginResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.base_plugin_flavor.BasePluginResponseMetadata)

Response metadata for action flavors.

#### config_schema *: Dict[str, Any]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config_schema': FieldInfo(annotation=Dict[str, Any], required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.action_flavor.ActionFlavorResponseResources(\*\*extra_data: Any)

Bases: [`BasePluginResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.base_plugin_flavor.BasePluginResponseResources)

Response resources for action flavors.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## zenml.models.v2.core.api_key module

Models representing API keys.

### *class* zenml.models.v2.core.api_key.APIKey(\*, id: UUID, key: str)

Bases: `BaseModel`

Encoded model for API keys.

#### *classmethod* decode_api_key(encoded_key: str) → [APIKey](#zenml.models.v2.core.api_key.APIKey)

Decodes an API key from a base64 string.

Args:
: encoded_key: The encoded API key.

Returns:
: The decoded API key.

Raises:
: ValueError: If the key is not valid.

#### encode() → str

Encodes the API key in a base64 string that includes the key ID and prefix.

Returns:
: The encoded API key.

#### id *: UUID*

#### key *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'id': FieldInfo(annotation=UUID, required=True), 'key': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.api_key.APIKeyFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, service_account: UUID | None = None, name: str | None = None, description: str | None = None, active: Annotated[bool | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, last_login: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, last_rotated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None)

Bases: [`BaseFilter`](zenml.models.v2.base.md#zenml.models.v2.base.filter.BaseFilter)

Filter model for API keys.

#### CLI_EXCLUDE_FIELDS *: ClassVar[List[str]]* *= ['service_account']*

#### FILTER_EXCLUDE_FIELDS *: ClassVar[List[str]]* *= ['sort_by', 'page', 'size', 'logical_operator', 'service_account']*

#### active *: bool | str | None*

#### apply_filter(query: AnyQuery, table: Type[AnySchema]) → AnyQuery

Override to apply the service account scope as an additional filter.

Args:
: query: The query to which to apply the filter.
  table: The query table.

Returns:
: The query with filter applied.

#### created *: datetime | str | None*

#### description *: str | None*

#### id *: UUID | str | None*

#### last_login *: datetime | str | None*

#### last_rotated *: datetime | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'active': FieldInfo(annotation=Union[bool, str, NoneType], required=False, default=None, title='Whether the API key is active.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Filter by the API key description.'), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'last_login': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, title='Time when the API key was last used to log in.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'last_rotated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, title='Time when the API key was last rotated.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Name of the API key'), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'service_account': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The service account to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str | None*

#### page *: int*

#### service_account *: UUID | None*

#### set_service_account(service_account_id: UUID) → None

Set the service account by which to scope this query.

Args:
: service_account_id: The service account ID.

#### size *: int*

#### sort_by *: str*

#### updated *: datetime | str | None*

### *class* zenml.models.v2.core.api_key.APIKeyInternalResponse(\*, body: [APIKeyResponseBody](#zenml.models.v2.core.api_key.APIKeyResponseBody) | None = None, metadata: [APIKeyResponseMetadata](#zenml.models.v2.core.api_key.APIKeyResponseMetadata) | None = None, resources: [APIKeyResponseResources](#zenml.models.v2.core.api_key.APIKeyResponseResources) | None = None, id: UUID, permission_denied: bool = False, name: Annotated[str, MaxLen(max_length=255)], previous_key: str | None = None)

Bases: [`APIKeyResponse`](#zenml.models.v2.core.api_key.APIKeyResponse)

Response model for API keys used internally.

#### body *: 'AnyBody' | None*

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[APIKeyResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[APIKeyResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the API Key.', metadata=[MaxLen(max_length=255)]), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'previous_key': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The previous API key. Only set if the key was rotated.'), 'resources': FieldInfo(annotation=Union[APIKeyResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str*

#### permission_denied *: bool*

#### previous_key *: str | None*

#### resources *: 'AnyResources' | None*

#### verify_key(key: str) → bool

Verifies a given key against the stored (hashed) key(s).

Args:
: key: Input key to be verified.

Returns:
: True if the keys match.

### *class* zenml.models.v2.core.api_key.APIKeyInternalUpdate(\*, name: Annotated[str | None, MaxLen(max_length=255)] = None, description: Annotated[str | None, MaxLen(max_length=65535)] = None, active: bool | None = None, update_last_login: bool = False)

Bases: [`APIKeyUpdate`](#zenml.models.v2.core.api_key.APIKeyUpdate)

Update model for API keys used internally.

#### active *: bool | None*

#### description *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'active': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, title='Whether the API key is active.'), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The description of the API Key.', metadata=[MaxLen(max_length=65535)]), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The name of the API Key.', metadata=[MaxLen(max_length=255)]), 'update_last_login': FieldInfo(annotation=bool, required=False, default=False, title='Whether to update the last login timestamp.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

#### update_last_login *: bool*

### *class* zenml.models.v2.core.api_key.APIKeyRequest(\*, name: Annotated[str, MaxLen(max_length=255)], description: Annotated[str | None, MaxLen(max_length=65535)] = None)

Bases: [`BaseRequest`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseRequest)

Request model for API keys.

#### description *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The description of the API Key.', metadata=[MaxLen(max_length=65535)]), 'name': FieldInfo(annotation=str, required=True, title='The name of the API Key.', metadata=[MaxLen(max_length=255)])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

### *class* zenml.models.v2.core.api_key.APIKeyResponse(\*, body: [APIKeyResponseBody](#zenml.models.v2.core.api_key.APIKeyResponseBody) | None = None, metadata: [APIKeyResponseMetadata](#zenml.models.v2.core.api_key.APIKeyResponseMetadata) | None = None, resources: [APIKeyResponseResources](#zenml.models.v2.core.api_key.APIKeyResponseResources) | None = None, id: UUID, permission_denied: bool = False, name: Annotated[str, MaxLen(max_length=255)])

Bases: `BaseIdentifiedResponse[APIKeyResponseBody, APIKeyResponseMetadata, APIKeyResponseResources]`

Response model for API keys.

#### *property* active *: bool*

The active property.

Returns:
: the value of the property.

#### body *: 'AnyBody' | None*

#### *property* description *: str*

The description property.

Returns:
: the value of the property.

#### get_hydrated_version() → [APIKeyResponse](#zenml.models.v2.core.api_key.APIKeyResponse)

Get the hydrated version of this API key.

Returns:
: an instance of the same entity with the metadata field attached.

#### id *: UUID*

#### *property* key *: str | None*

The key property.

Returns:
: the value of the property.

#### *property* last_login *: datetime | None*

The last_login property.

Returns:
: the value of the property.

#### *property* last_rotated *: datetime | None*

The last_rotated property.

Returns:
: the value of the property.

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[APIKeyResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[APIKeyResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the API Key.', metadata=[MaxLen(max_length=255)]), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[APIKeyResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str*

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* retain_period_minutes *: int*

The retain_period_minutes property.

Returns:
: the value of the property.

#### *property* service_account *: [ServiceAccountResponse](zenml.models.md#zenml.models.ServiceAccountResponse)*

The service_account property.

Returns:
: the value of the property.

#### set_key(key: str) → None

Sets the API key and encodes it.

Args:
: key: The API key value to be set.

### *class* zenml.models.v2.core.api_key.APIKeyResponseBody(\*, created: datetime, updated: datetime, key: str | None = None, active: bool = True, service_account: [ServiceAccountResponse](#zenml.models.v2.core.service_account.ServiceAccountResponse))

Bases: [`BaseDatedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseDatedResponseBody)

Response body for API keys.

#### active *: bool*

#### created *: datetime*

#### key *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'active': FieldInfo(annotation=bool, required=False, default=True, title='Whether the API key is active.'), 'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'key': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The API key. Only set immediately after creation or rotation.'), 'service_account': FieldInfo(annotation=ServiceAccountResponse, required=True, title='The service account associated with this API key.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### service_account *: [ServiceAccountResponse](zenml.models.md#zenml.models.ServiceAccountResponse)*

#### updated *: datetime*

### *class* zenml.models.v2.core.api_key.APIKeyResponseMetadata(\*, description: Annotated[str, MaxLen(max_length=65535)] = '', retain_period_minutes: int, last_login: datetime | None = None, last_rotated: datetime | None = None)

Bases: [`BaseResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseMetadata)

Response metadata for API keys.

#### description *: str*

#### last_login *: datetime | None*

#### last_rotated *: datetime | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'description': FieldInfo(annotation=str, required=False, default='', title='The description of the API Key.', metadata=[MaxLen(max_length=65535)]), 'last_login': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None, title='Time when the API key was last used to log in.'), 'last_rotated': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None, title='Time when the API key was last rotated.'), 'retain_period_minutes': FieldInfo(annotation=int, required=True, title='Number of minutes for which the previous key is still valid after it has been rotated.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### retain_period_minutes *: int*

### *class* zenml.models.v2.core.api_key.APIKeyResponseResources(\*\*extra_data: Any)

Bases: [`BaseResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseResources)

Class for all resource models associated with the APIKey entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.api_key.APIKeyRotateRequest(\*, retain_period_minutes: int = 0)

Bases: `BaseModel`

Request model for API key rotation.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'retain_period_minutes': FieldInfo(annotation=int, required=False, default=0, title='Number of minutes for which the previous key is still valid after it has been rotated.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### retain_period_minutes *: int*

### *class* zenml.models.v2.core.api_key.APIKeyUpdate(\*, name: Annotated[str | None, MaxLen(max_length=255)] = None, description: Annotated[str | None, MaxLen(max_length=65535)] = None, active: bool | None = None)

Bases: [`BaseUpdate`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseUpdate)

Update model for API keys.

#### active *: bool | None*

#### description *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'active': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, title='Whether the API key is active.'), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The description of the API Key.', metadata=[MaxLen(max_length=65535)]), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The name of the API Key.', metadata=[MaxLen(max_length=255)])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

## zenml.models.v2.core.artifact module

Models representing artifacts.

### *class* zenml.models.v2.core.artifact.ArtifactFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None, tag: str | None = None, name: str | None = None, has_custom_name: bool | None = None)

Bases: [`WorkspaceScopedTaggableFilter`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedTaggableFilter)

Model to enable advanced filtering of artifacts.

#### created *: datetime | str | None*

#### has_custom_name *: bool | None*

#### id *: UUID | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'has_custom_name': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'tag': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Tag to apply to the filter query.'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str | None*

#### page *: int*

#### scope_workspace *: UUID | None*

#### size *: int*

#### sort_by *: str*

#### tag *: str | None*

#### updated *: datetime | str | None*

### *class* zenml.models.v2.core.artifact.ArtifactRequest(\*, name: Annotated[str, MaxLen(max_length=255)], has_custom_name: bool = False, tags: List[str] | None = None)

Bases: [`BaseRequest`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseRequest)

Artifact request model.

#### has_custom_name *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'has_custom_name': FieldInfo(annotation=bool, required=False, default=False, title='Whether the name is custom (True) or auto-generated (False).'), 'name': FieldInfo(annotation=str, required=True, title='Name of the artifact.', metadata=[MaxLen(max_length=255)]), 'tags': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None, title='Artifact tags.', description="Should be a list of plain strings, e.g., ['tag1', 'tag2']")}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### tags *: List[str] | None*

### *class* zenml.models.v2.core.artifact.ArtifactResponse(\*, body: [ArtifactResponseBody](#zenml.models.v2.core.artifact.ArtifactResponseBody) | None = None, metadata: [ArtifactResponseMetadata](#zenml.models.v2.core.artifact.ArtifactResponseMetadata) | None = None, resources: [ArtifactResponseResources](#zenml.models.v2.core.artifact.ArtifactResponseResources) | None = None, id: UUID, permission_denied: bool = False, name: Annotated[str, MaxLen(max_length=255)])

Bases: `BaseIdentifiedResponse[ArtifactResponseBody, ArtifactResponseMetadata, ArtifactResponseResources]`

Artifact response model.

#### body *: 'AnyBody' | None*

#### get_hydrated_version() → [ArtifactResponse](#zenml.models.v2.core.artifact.ArtifactResponse)

Get the hydrated version of this artifact.

Returns:
: an instance of the same entity with the metadata field attached.

#### *property* has_custom_name *: bool*

The has_custom_name property.

Returns:
: the value of the property.

#### id *: UUID*

#### *property* latest_version_id *: UUID | None*

The latest_version_id property.

Returns:
: the value of the property.

#### *property* latest_version_name *: str | None*

The latest_version_name property.

Returns:
: the value of the property.

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[ArtifactResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[ArtifactResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='Name of the output in the parent step.', metadata=[MaxLen(max_length=255)]), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[ArtifactResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str*

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* tags *: List[[TagResponse](#zenml.models.v2.core.tag.TagResponse)]*

The tags property.

Returns:
: the value of the property.

#### *property* versions *: Dict[str, [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse)]*

Get a list of all versions of this artifact.

Returns:
: A list of all versions of this artifact.

### *class* zenml.models.v2.core.artifact.ArtifactResponseBody(\*, created: datetime, updated: datetime, tags: List[[TagResponse](#zenml.models.v2.core.tag.TagResponse)], latest_version_name: str | None = None, latest_version_id: UUID | None = None)

Bases: [`BaseDatedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseDatedResponseBody)

Response body for artifacts.

#### created *: datetime*

#### latest_version_id *: UUID | None*

#### latest_version_name *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'latest_version_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'latest_version_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'tags': FieldInfo(annotation=List[TagResponse], required=True, title='Tags associated with the model'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### tags *: List[[TagResponse](#zenml.models.v2.core.tag.TagResponse)]*

#### updated *: datetime*

### *class* zenml.models.v2.core.artifact.ArtifactResponseMetadata(\*, has_custom_name: bool = False)

Bases: [`BaseResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseMetadata)

Response metadata for artifacts.

#### has_custom_name *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'has_custom_name': FieldInfo(annotation=bool, required=False, default=False, title='Whether the name is custom (True) or auto-generated (False).')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.artifact.ArtifactResponseResources(\*\*extra_data: Any)

Bases: [`BaseResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseResources)

Class for all resource models associated with the Artifact Entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.artifact.ArtifactUpdate(\*, name: str | None = None, add_tags: List[str] | None = None, remove_tags: List[str] | None = None, has_custom_name: bool | None = None)

Bases: `BaseModel`

Artifact update model.

#### add_tags *: List[str] | None*

#### has_custom_name *: bool | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'add_tags': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None), 'has_custom_name': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'remove_tags': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

#### remove_tags *: List[str] | None*

## zenml.models.v2.core.artifact_version module

Models representing artifact versions.

### *class* zenml.models.v2.core.artifact_version.ArtifactVersionFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None, tag: str | None = None, artifact_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, name: str | None = None, version: str | None = None, version_number: Annotated[int | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, uri: str | None = None, materializer: str | None = None, type: str | None = None, data_type: str | None = None, artifact_store_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, workspace_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, user_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, only_unused: bool | None = False, has_custom_name: bool | None = None)

Bases: [`WorkspaceScopedTaggableFilter`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedTaggableFilter)

Model to enable advanced filtering of artifact versions.

#### FILTER_EXCLUDE_FIELDS *: ClassVar[List[str]]* *= ['sort_by', 'page', 'size', 'logical_operator', 'scope_workspace', 'tag', 'name', 'only_unused', 'has_custom_name']*

#### artifact_id *: UUID | str | None*

#### artifact_store_id *: UUID | str | None*

#### created *: datetime | str | None*

#### data_type *: str | None*

#### get_custom_filters() → List[ColumnElement[bool]]

Get custom filters.

Returns:
: A list of custom filters.

#### has_custom_name *: bool | None*

#### id *: UUID | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### materializer *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='ID of the artifact to which this version belongs.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'artifact_store_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Artifact store for this artifact', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'data_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Datatype of the artifact'), 'has_custom_name': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, description='Filter only artifacts with/without custom names.'), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'materializer': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Materializer used to produce the artifact'), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Name of the artifact to which this version belongs.'), 'only_unused': FieldInfo(annotation=Union[bool, NoneType], required=False, default=False, description='Filter only for unused artifacts'), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'tag': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Tag to apply to the filter query.'), 'type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Type of the artifact'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'uri': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Uri of the artifact'), 'user_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='User that produced this artifact', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Version of the artifact'), 'version_number': FieldInfo(annotation=Union[int, str, NoneType], required=False, default=None, description='Version of the artifact if it is an integer', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'workspace_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Workspace for this artifact', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str | None*

#### only_unused *: bool | None*

#### page *: int*

#### scope_workspace *: UUID | None*

#### size *: int*

#### sort_by *: str*

#### tag *: str | None*

#### type *: str | None*

#### updated *: datetime | str | None*

#### uri *: str | None*

#### user_id *: UUID | str | None*

#### version *: str | None*

#### version_number *: int | str | None*

#### workspace_id *: UUID | str | None*

### *class* zenml.models.v2.core.artifact_version.ArtifactVersionRequest(\*, user: UUID, workspace: UUID, artifact_id: UUID, version: Annotated[str | int, \_PydanticGeneralMetadata(union_mode='left_to_right')], has_custom_name: bool = False, type: [ArtifactType](zenml.md#zenml.enums.ArtifactType), artifact_store_id: UUID | None = None, uri: Annotated[str, MaxLen(max_length=65535)], materializer: Annotated[[Source](zenml.config.md#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)], data_type: Annotated[[Source](zenml.config.md#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)], tags: List[str] | None = None, visualizations: List[[ArtifactVisualizationRequest](#zenml.models.v2.core.artifact_visualization.ArtifactVisualizationRequest)] | None = None)

Bases: [`WorkspaceScopedRequest`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedRequest)

Request model for artifact versions.

#### artifact_id *: UUID*

#### artifact_store_id *: UUID | None*

#### data_type *: Annotated[[Source](zenml.config.md#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)]*

#### has_custom_name *: bool*

#### materializer *: Annotated[[Source](zenml.config.md#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact_id': FieldInfo(annotation=UUID, required=True, title='ID of the artifact to which this version belongs.'), 'artifact_store_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='ID of the artifact store in which this artifact is stored.'), 'data_type': FieldInfo(annotation=Source, required=True, title='Data type of the artifact.', metadata=[SerializeAsAny(), BeforeValidator(func=<function convert_source>)]), 'has_custom_name': FieldInfo(annotation=bool, required=False, default=False, title='Whether the name is custom (True) or auto-generated (False).'), 'materializer': FieldInfo(annotation=Source, required=True, title='Materializer class to use for this artifact.', metadata=[SerializeAsAny(), BeforeValidator(func=<function convert_source>)]), 'tags': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None, title='Tags of the artifact.', description="Should be a list of plain strings, e.g., ['tag1', 'tag2']"), 'type': FieldInfo(annotation=ArtifactType, required=True, title='Type of the artifact.'), 'uri': FieldInfo(annotation=str, required=True, title='URI of the artifact.', metadata=[MaxLen(max_length=65535)]), 'user': FieldInfo(annotation=UUID, required=True, title='The id of the user that created this resource.'), 'version': FieldInfo(annotation=Union[str, int], required=True, title='Version of the artifact.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'visualizations': FieldInfo(annotation=Union[List[ArtifactVisualizationRequest], NoneType], required=False, default=None, title='Visualizations of the artifact.'), 'workspace': FieldInfo(annotation=UUID, required=True, title='The workspace to which this resource belongs.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### *classmethod* str_field_max_length_check(value: Any) → Any

Checks if the length of the value exceeds the maximum str length.

Args:
: value: the value set in the field

Returns:
: the value itself.

Raises:
: AssertionError: if the length of the field is longer than the
  : maximum threshold.

#### tags *: List[str] | None*

#### type *: [ArtifactType](zenml.md#zenml.enums.ArtifactType)*

#### uri *: str*

#### user *: UUID*

#### version *: str | int*

#### visualizations *: List[[ArtifactVisualizationRequest](zenml.models.md#zenml.models.ArtifactVisualizationRequest)] | None*

#### workspace *: UUID*

### *class* zenml.models.v2.core.artifact_version.ArtifactVersionResponse(\*, body: [ArtifactVersionResponseBody](#zenml.models.v2.core.artifact_version.ArtifactVersionResponseBody) | None = None, metadata: [ArtifactVersionResponseMetadata](#zenml.models.v2.core.artifact_version.ArtifactVersionResponseMetadata) | None = None, resources: [ArtifactVersionResponseResources](#zenml.models.v2.core.artifact_version.ArtifactVersionResponseResources) | None = None, id: UUID, permission_denied: bool = False)

Bases: `WorkspaceScopedResponse[ArtifactVersionResponseBody, ArtifactVersionResponseMetadata, ArtifactVersionResponseResources]`

Response model for artifact versions.

#### *property* artifact *: [ArtifactResponse](#zenml.models.v2.core.artifact.ArtifactResponse)*

The artifact property.

Returns:
: the value of the property.

#### *property* artifact_store_id *: UUID | None*

The artifact_store_id property.

Returns:
: the value of the property.

#### body *: 'AnyBody' | None*

#### *property* data_type *: [Source](zenml.config.md#zenml.config.source.Source)*

The data_type property.

Returns:
: the value of the property.

#### download_files(path: str, overwrite: bool = False) → None

Downloads data for an artifact with no materializing.

Any artifacts will be saved as a zip file to the given path.

Args:
: path: The path to save the binary data to.
  overwrite: Whether to overwrite the file if it already exists.

Raises:
: ValueError: If the path does not end with ‘.zip’.

#### get_hydrated_version() → [ArtifactVersionResponse](#zenml.models.v2.core.artifact_version.ArtifactVersionResponse)

Get the hydrated version of this artifact version.

Returns:
: an instance of the same entity with the metadata field attached.

#### id *: UUID*

#### load() → Any

Materializes (loads) the data stored in this artifact.

Returns:
: The materialized data.

#### *property* materializer *: [Source](zenml.config.md#zenml.config.source.Source)*

The materializer property.

Returns:
: the value of the property.

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[ArtifactVersionResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[ArtifactVersionResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[ArtifactVersionResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### *property* name *: str*

The name property.

Returns:
: the value of the property.

#### permission_denied *: bool*

#### *property* producer_pipeline_run_id *: UUID | None*

The producer_pipeline_run_id property.

Returns:
: the value of the property.

#### *property* producer_step_run_id *: UUID | None*

The producer_step_run_id property.

Returns:
: the value of the property.

#### read() → Any

(Deprecated) Materializes (loads) the data stored in this artifact.

Returns:
: The materialized data.

#### resources *: 'AnyResources' | None*

#### *property* run *: [PipelineRunResponse](zenml.models.md#zenml.models.PipelineRunResponse)*

Get the pipeline run that produced this artifact.

Returns:
: The pipeline run that produced this artifact.

#### *property* run_metadata *: Dict[str, [RunMetadataResponse](zenml.models.md#zenml.models.RunMetadataResponse)]*

The metadata property.

Returns:
: the value of the property.

#### *property* step *: [StepRunResponse](zenml.models.md#zenml.models.StepRunResponse)*

Get the step that produced this artifact.

Returns:
: The step that produced this artifact.

#### *property* tags *: List[[TagResponse](#zenml.models.v2.core.tag.TagResponse)]*

The tags property.

Returns:
: the value of the property.

#### *property* type *: [ArtifactType](zenml.md#zenml.enums.ArtifactType)*

The type property.

Returns:
: the value of the property.

#### *property* uri *: str*

The uri property.

Returns:
: the value of the property.

#### *property* version *: str | int*

The version property.

Returns:
: the value of the property.

#### *property* visualizations *: List[[ArtifactVisualizationResponse](zenml.models.md#zenml.models.ArtifactVisualizationResponse)] | None*

The visualizations property.

Returns:
: the value of the property.

#### visualize(title: str | None = None) → None

Visualize the artifact in notebook environments.

Args:
: title: Optional title to show before the visualizations.

### *class* zenml.models.v2.core.artifact_version.ArtifactVersionResponseBody(\*, created: datetime, updated: datetime, user: [UserResponse](#zenml.models.v2.core.user.UserResponse) | None = None, artifact: [ArtifactResponse](#zenml.models.v2.core.artifact.ArtifactResponse), version: str, uri: Annotated[str, MaxLen(max_length=65535)], type: [ArtifactType](zenml.md#zenml.enums.ArtifactType), materializer: Annotated[[Source](zenml.config.md#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)], data_type: Annotated[[Source](zenml.config.md#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)], tags: List[[TagResponse](#zenml.models.v2.core.tag.TagResponse)], producer_pipeline_run_id: UUID | None = None)

Bases: [`WorkspaceScopedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseBody)

Response body for artifact versions.

#### artifact *: [ArtifactResponse](#zenml.models.v2.core.artifact.ArtifactResponse)*

#### created *: datetime*

#### data_type *: Annotated[[Source](zenml.config.md#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)]*

#### materializer *: Annotated[[Source](zenml.config.md#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact': FieldInfo(annotation=ArtifactResponse, required=True, title='Artifact to which this version belongs.'), 'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'data_type': FieldInfo(annotation=Source, required=True, title='Data type of the artifact.', metadata=[SerializeAsAny(), BeforeValidator(func=<function convert_source>)]), 'materializer': FieldInfo(annotation=Source, required=True, title='Materializer class to use for this artifact.', metadata=[SerializeAsAny(), BeforeValidator(func=<function convert_source>)]), 'producer_pipeline_run_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The ID of the pipeline run that generated this artifact version.'), 'tags': FieldInfo(annotation=List[TagResponse], required=True, title='Tags associated with the model'), 'type': FieldInfo(annotation=ArtifactType, required=True, title='Type of the artifact.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.'), 'uri': FieldInfo(annotation=str, required=True, title='URI of the artifact.', metadata=[MaxLen(max_length=65535)]), 'user': FieldInfo(annotation=Union[UserResponse, NoneType], required=False, default=None, title='The user who created this resource.'), 'version': FieldInfo(annotation=str, required=True, title='Version of the artifact.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### producer_pipeline_run_id *: UUID | None*

#### *classmethod* str_field_max_length_check(value: Any) → Any

Checks if the length of the value exceeds the maximum str length.

Args:
: value: the value set in the field

Returns:
: the value itself.

Raises:
: AssertionError: if the length of the field is longer than the
  : maximum threshold.

#### tags *: List[[TagResponse](#zenml.models.v2.core.tag.TagResponse)]*

#### type *: [ArtifactType](zenml.md#zenml.enums.ArtifactType)*

#### updated *: datetime*

#### uri *: str*

#### user *: 'UserResponse' | None*

#### version *: str*

### *class* zenml.models.v2.core.artifact_version.ArtifactVersionResponseMetadata(\*, workspace: [WorkspaceResponse](#zenml.models.v2.core.workspace.WorkspaceResponse), artifact_store_id: UUID | None = None, producer_step_run_id: UUID | None = None, visualizations: List[[ArtifactVisualizationResponse](#zenml.models.v2.core.artifact_visualization.ArtifactVisualizationResponse)] | None = None, run_metadata: Dict[str, [RunMetadataResponse](#zenml.models.v2.core.run_metadata.RunMetadataResponse)] = {})

Bases: [`WorkspaceScopedResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseMetadata)

Response metadata for artifact versions.

#### artifact_store_id *: UUID | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact_store_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='ID of the artifact store in which this artifact is stored.'), 'producer_step_run_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='ID of the step run that produced this artifact.'), 'run_metadata': FieldInfo(annotation=Dict[str, RunMetadataResponse], required=False, default={}, title='Metadata of the artifact.'), 'visualizations': FieldInfo(annotation=Union[List[ArtifactVisualizationResponse], NoneType], required=False, default=None, title='Visualizations of the artifact.'), 'workspace': FieldInfo(annotation=WorkspaceResponse, required=True, title='The workspace of this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### producer_step_run_id *: UUID | None*

#### run_metadata *: Dict[str, [RunMetadataResponse](zenml.models.md#zenml.models.RunMetadataResponse)]*

#### visualizations *: List[[ArtifactVisualizationResponse](zenml.models.md#zenml.models.ArtifactVisualizationResponse)] | None*

#### workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

### *class* zenml.models.v2.core.artifact_version.ArtifactVersionResponseResources(\*\*extra_data: Any)

Bases: [`WorkspaceScopedResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseResources)

Class for all resource models associated with the artifact version entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.artifact_version.ArtifactVersionUpdate(\*, name: str | None = None, add_tags: List[str] | None = None, remove_tags: List[str] | None = None)

Bases: `BaseModel`

Artifact version update model.

#### add_tags *: List[str] | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'add_tags': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'remove_tags': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

#### remove_tags *: List[str] | None*

### *class* zenml.models.v2.core.artifact_version.LazyArtifactVersionResponse(\*, body: [ArtifactVersionResponseBody](#zenml.models.v2.core.artifact_version.ArtifactVersionResponseBody) | None = None, metadata: [ArtifactVersionResponseMetadata](#zenml.models.v2.core.artifact_version.ArtifactVersionResponseMetadata) | None = None, resources: [ArtifactVersionResponseResources](#zenml.models.v2.core.artifact_version.ArtifactVersionResponseResources) | None = None, id: UUID | None = None, permission_denied: bool = False, lazy_load_name: str | None = None, lazy_load_version: str | None = None, lazy_load_model: [Model](zenml.model.md#zenml.model.model.Model))

Bases: [`ArtifactVersionResponse`](#zenml.models.v2.core.artifact_version.ArtifactVersionResponse)

Lazy artifact version response.

Used if the artifact version is accessed from the model in
a pipeline context available only during pipeline compilation.

#### get_body() → None

Protects from misuse of the lazy loader.

Raises:
: RuntimeError: always

#### get_metadata() → None

Protects from misuse of the lazy loader.

Raises:
: RuntimeError: always

#### id *: UUID | None*

#### lazy_load_model *: [Model](zenml.model.md#zenml.model.model.Model)*

#### lazy_load_name *: str | None*

#### lazy_load_version *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[ArtifactVersionResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'lazy_load_model': FieldInfo(annotation=Model, required=True), 'lazy_load_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'lazy_load_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'metadata': FieldInfo(annotation=Union[ArtifactVersionResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[ArtifactVersionResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### *property* run_metadata *: Dict[str, [RunMetadataResponse](zenml.models.md#zenml.models.RunMetadataResponse)]*

The metadata property in lazy loading mode.

Returns:
: getter of lazy responses for internal use.

## zenml.models.v2.core.artifact_visualization module

Models representing artifact visualizations.

### *class* zenml.models.v2.core.artifact_visualization.ArtifactVisualizationRequest(\*, type: [VisualizationType](zenml.md#zenml.enums.VisualizationType), uri: str)

Bases: [`BaseRequest`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseRequest)

Request model for artifact visualization.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'type': FieldInfo(annotation=VisualizationType, required=True), 'uri': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: [VisualizationType](zenml.md#zenml.enums.VisualizationType)*

#### uri *: str*

### *class* zenml.models.v2.core.artifact_visualization.ArtifactVisualizationResponse(\*, body: [ArtifactVisualizationResponseBody](#zenml.models.v2.core.artifact_visualization.ArtifactVisualizationResponseBody) | None = None, metadata: [ArtifactVisualizationResponseMetadata](#zenml.models.v2.core.artifact_visualization.ArtifactVisualizationResponseMetadata) | None = None, resources: [ArtifactVisualizationResponseResources](#zenml.models.v2.core.artifact_visualization.ArtifactVisualizationResponseResources) | None = None, id: UUID, permission_denied: bool = False)

Bases: `BaseIdentifiedResponse[ArtifactVisualizationResponseBody, ArtifactVisualizationResponseMetadata, ArtifactVisualizationResponseResources]`

Response model for artifact visualizations.

#### *property* artifact_version_id *: UUID*

The artifact_version_id property.

Returns:
: the value of the property.

#### body *: 'AnyBody' | None*

#### get_hydrated_version() → [ArtifactVisualizationResponse](#zenml.models.v2.core.artifact_visualization.ArtifactVisualizationResponse)

Get the hydrated version of this artifact visualization.

Returns:
: an instance of the same entity with the metadata field attached.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[ArtifactVisualizationResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[ArtifactVisualizationResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[ArtifactVisualizationResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* type *: [VisualizationType](zenml.md#zenml.enums.VisualizationType)*

The type property.

Returns:
: the value of the property.

#### *property* uri *: str*

The uri property.

Returns:
: the value of the property.

### *class* zenml.models.v2.core.artifact_visualization.ArtifactVisualizationResponseBody(\*, created: datetime, updated: datetime, type: [VisualizationType](zenml.md#zenml.enums.VisualizationType), uri: str)

Bases: [`BaseDatedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseDatedResponseBody)

Response body for artifact visualizations.

#### created *: datetime*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'type': FieldInfo(annotation=VisualizationType, required=True), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.'), 'uri': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: [VisualizationType](zenml.md#zenml.enums.VisualizationType)*

#### updated *: datetime*

#### uri *: str*

### *class* zenml.models.v2.core.artifact_visualization.ArtifactVisualizationResponseMetadata(\*, artifact_version_id: UUID)

Bases: [`BaseResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseMetadata)

Response metadata model for artifact visualizations.

#### artifact_version_id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact_version_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.artifact_visualization.ArtifactVisualizationResponseResources(\*\*extra_data: Any)

Bases: [`BaseResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseResources)

Class for all resource models associated with the artifact visualization.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## zenml.models.v2.core.code_reference module

Models representing code references.

### *class* zenml.models.v2.core.code_reference.CodeReferenceRequest(\*, commit: str, subdirectory: str, code_repository: UUID)

Bases: [`BaseRequest`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseRequest)

Request model for code references.

#### code_repository *: UUID*

#### commit *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'code_repository': FieldInfo(annotation=UUID, required=True, description='The repository of the code reference.'), 'commit': FieldInfo(annotation=str, required=True, description='The commit of the code reference.'), 'subdirectory': FieldInfo(annotation=str, required=True, description='The subdirectory of the code reference.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### subdirectory *: str*

### *class* zenml.models.v2.core.code_reference.CodeReferenceResponse(\*, body: [CodeReferenceResponseBody](#zenml.models.v2.core.code_reference.CodeReferenceResponseBody) | None = None, metadata: [CodeReferenceResponseMetadata](#zenml.models.v2.core.code_reference.CodeReferenceResponseMetadata) | None = None, resources: [CodeReferenceResponseResources](#zenml.models.v2.core.code_reference.CodeReferenceResponseResources) | None = None, id: UUID, permission_denied: bool = False)

Bases: `BaseIdentifiedResponse[CodeReferenceResponseBody, CodeReferenceResponseMetadata, CodeReferenceResponseResources]`

Response model for code references.

#### body *: 'AnyBody' | None*

#### *property* code_repository *: [CodeRepositoryResponse](zenml.models.md#zenml.models.CodeRepositoryResponse)*

The code_repository property.

Returns:
: the value of the property.

#### *property* commit *: str*

The commit property.

Returns:
: the value of the property.

#### get_hydrated_version() → [CodeReferenceResponse](#zenml.models.v2.core.code_reference.CodeReferenceResponse)

Get the hydrated version of this code reference.

Returns:
: an instance of the same entity with the metadata field attached.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[CodeReferenceResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[CodeReferenceResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[CodeReferenceResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* subdirectory *: str*

The subdirectory property.

Returns:
: the value of the property.

### *class* zenml.models.v2.core.code_reference.CodeReferenceResponseBody(\*, created: datetime, updated: datetime, commit: str, subdirectory: str, code_repository: [CodeRepositoryResponse](#zenml.models.v2.core.code_repository.CodeRepositoryResponse))

Bases: [`BaseDatedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseDatedResponseBody)

Response body for code references.

#### code_repository *: [CodeRepositoryResponse](zenml.models.md#zenml.models.CodeRepositoryResponse)*

#### commit *: str*

#### created *: datetime*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'code_repository': FieldInfo(annotation=CodeRepositoryResponse, required=True, description='The repository of the code reference.'), 'commit': FieldInfo(annotation=str, required=True, description='The commit of the code reference.'), 'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'subdirectory': FieldInfo(annotation=str, required=True, description='The subdirectory of the code reference.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### subdirectory *: str*

#### updated *: datetime*

### *class* zenml.models.v2.core.code_reference.CodeReferenceResponseMetadata

Bases: [`BaseResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseMetadata)

Response metadata for code references.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.code_reference.CodeReferenceResponseResources(\*\*extra_data: Any)

Bases: [`BaseResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseResources)

Class for all resource models associated with the code reference entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## zenml.models.v2.core.code_repository module

Models representing code repositories.

### *class* zenml.models.v2.core.code_repository.CodeRepositoryFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None, name: str | None = None, workspace_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, user_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None)

Bases: [`WorkspaceScopedFilter`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedFilter)

Model to enable advanced filtering of all code repositories.

#### created *: datetime | str | None*

#### id *: UUID | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Name of the code repository.'), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'user_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='User that created the code repository.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'workspace_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Workspace of the code repository.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str | None*

#### page *: int*

#### scope_workspace *: UUID | None*

#### size *: int*

#### sort_by *: str*

#### updated *: datetime | str | None*

#### user_id *: UUID | str | None*

#### workspace_id *: UUID | str | None*

### *class* zenml.models.v2.core.code_repository.CodeRepositoryRequest(\*, user: UUID, workspace: UUID, name: Annotated[str, MaxLen(max_length=255)], config: Dict[str, Any], source: [Source](zenml.config.md#zenml.config.source.Source), logo_url: str | None = None, description: Annotated[str | None, MaxLen(max_length=65535)] = None)

Bases: [`WorkspaceScopedRequest`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedRequest)

Request model for code repositories.

#### config *: Dict[str, Any]*

#### description *: str | None*

#### logo_url *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config': FieldInfo(annotation=Dict[str, Any], required=True, description='Configuration for the code repository.'), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Code repository description.', metadata=[MaxLen(max_length=65535)]), 'logo_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Optional URL of a logo (png, jpg or svg) for the code repository.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the code repository.', metadata=[MaxLen(max_length=255)]), 'source': FieldInfo(annotation=Source, required=True, description='The code repository source.'), 'user': FieldInfo(annotation=UUID, required=True, title='The id of the user that created this resource.'), 'workspace': FieldInfo(annotation=UUID, required=True, title='The workspace to which this resource belongs.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### source *: [Source](zenml.config.md#zenml.config.source.Source)*

#### user *: UUID*

#### workspace *: UUID*

### *class* zenml.models.v2.core.code_repository.CodeRepositoryResponse(\*, body: [CodeRepositoryResponseBody](#zenml.models.v2.core.code_repository.CodeRepositoryResponseBody) | None = None, metadata: [CodeRepositoryResponseMetadata](#zenml.models.v2.core.code_repository.CodeRepositoryResponseMetadata) | None = None, resources: [CodeRepositoryResponseResources](#zenml.models.v2.core.code_repository.CodeRepositoryResponseResources) | None = None, id: UUID, permission_denied: bool = False, name: Annotated[str, MaxLen(max_length=255)])

Bases: `WorkspaceScopedResponse[CodeRepositoryResponseBody, CodeRepositoryResponseMetadata, CodeRepositoryResponseResources]`

Response model for code repositories.

#### body *: 'AnyBody' | None*

#### *property* config *: Dict[str, Any]*

The config property.

Returns:
: the value of the property.

#### *property* description *: str | None*

The description property.

Returns:
: the value of the property.

#### get_hydrated_version() → [CodeRepositoryResponse](#zenml.models.v2.core.code_repository.CodeRepositoryResponse)

Get the hydrated version of this code repository.

Returns:
: an instance of the same entity with the metadata field attached.

#### id *: UUID*

#### *property* logo_url *: str | None*

The logo_url property.

Returns:
: the value of the property.

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[CodeRepositoryResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[CodeRepositoryResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the code repository.', metadata=[MaxLen(max_length=255)]), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[CodeRepositoryResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str*

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* source *: [Source](zenml.config.md#zenml.config.source.Source)*

The source property.

Returns:
: the value of the property.

### *class* zenml.models.v2.core.code_repository.CodeRepositoryResponseBody(\*, created: datetime, updated: datetime, user: [UserResponse](#zenml.models.v2.core.user.UserResponse) | None = None, source: [Source](zenml.config.md#zenml.config.source.Source), logo_url: str | None = None)

Bases: [`WorkspaceScopedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseBody)

Response body for code repositories.

#### created *: datetime*

#### logo_url *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'logo_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Optional URL of a logo (png, jpg or svg) for the code repository.'), 'source': FieldInfo(annotation=Source, required=True, description='The code repository source.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.'), 'user': FieldInfo(annotation=Union[UserResponse, NoneType], required=False, default=None, title='The user who created this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### source *: [Source](zenml.config.md#zenml.config.source.Source)*

#### updated *: datetime*

#### user *: 'UserResponse' | None*

### *class* zenml.models.v2.core.code_repository.CodeRepositoryResponseMetadata(\*, workspace: [WorkspaceResponse](#zenml.models.v2.core.workspace.WorkspaceResponse), config: Dict[str, Any], description: Annotated[str | None, MaxLen(max_length=65535)] = None)

Bases: [`WorkspaceScopedResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseMetadata)

Response metadata for code repositories.

#### config *: Dict[str, Any]*

#### description *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config': FieldInfo(annotation=Dict[str, Any], required=True, description='Configuration for the code repository.'), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Code repository description.', metadata=[MaxLen(max_length=65535)]), 'workspace': FieldInfo(annotation=WorkspaceResponse, required=True, title='The workspace of this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

### *class* zenml.models.v2.core.code_repository.CodeRepositoryResponseResources(\*\*extra_data: Any)

Bases: [`WorkspaceScopedResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseResources)

Class for all resource models associated with the code repository entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.code_repository.CodeRepositoryUpdate(\*, name: Annotated[str | None, MaxLen(max_length=255)] = None, config: Dict[str, Any] | None = None, source: Annotated[[Source](zenml.config.md#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)] | None = None, logo_url: str | None = None, description: Annotated[str | None, MaxLen(max_length=65535)] = None)

Bases: [`BaseUpdate`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseUpdate)

Update model for code repositories.

#### config *: Dict[str, Any] | None*

#### description *: str | None*

#### logo_url *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, description='Configuration for the code repository.'), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Code repository description.', metadata=[MaxLen(max_length=65535)]), 'logo_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Optional URL of a logo (png, jpg or svg) for the code repository.'), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The name of the code repository.', metadata=[MaxLen(max_length=255)]), 'source': FieldInfo(annotation=Union[Annotated[Source, SerializeAsAny, BeforeValidator], NoneType], required=False, default=None, description='The code repository source.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

#### source *: Annotated[[Source](zenml.config.md#zenml.config.source.Source), SerializeAsAny(), BeforeValidator(func=convert_source)] | None*

## zenml.models.v2.core.component module

Models representing components.

### *class* zenml.models.v2.core.component.ComponentBase(\*, name: Annotated[str, MaxLen(max_length=255)], type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), flavor: Annotated[str, MaxLen(max_length=255)], configuration: Dict[str, Any], connector_resource_id: str | None = None, labels: Dict[str, Any] | None = None, component_spec_path: str | None = None)

Bases: `BaseModel`

Base model for components.

#### component_spec_path *: str | None*

#### configuration *: Dict[str, Any]*

#### connector_resource_id *: str | None*

#### flavor *: str*

#### labels *: Dict[str, Any] | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'component_spec_path': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The path to the component spec used for mlstacks deployments.'), 'configuration': FieldInfo(annotation=Dict[str, Any], required=True, title='The stack component configuration.'), 'connector_resource_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The ID of a specific resource instance to gain access to through the connector'), 'flavor': FieldInfo(annotation=str, required=True, title='The flavor of the stack component.', metadata=[MaxLen(max_length=255)]), 'labels': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, title='The stack component labels.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the stack component.', metadata=[MaxLen(max_length=255)]), 'type': FieldInfo(annotation=StackComponentType, required=True, title='The type of the stack component.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

### *class* zenml.models.v2.core.component.ComponentFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None, scope_type: str | None = None, name: str | None = None, flavor: str | None = None, type: str | None = None, workspace_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, user_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, connector_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, stack_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None)

Bases: [`WorkspaceScopedFilter`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedFilter)

Model to enable advanced filtering of all ComponentModels.

The Component Model needs additional scoping. As such the \_scope_user
field can be set to the user that is doing the filtering. The
generate_filter() method of the baseclass is overwritten to include the
scoping.

#### CLI_EXCLUDE_FIELDS *: ClassVar[List[str]]* *= ['scope_workspace', 'scope_type']*

#### FILTER_EXCLUDE_FIELDS *: ClassVar[List[str]]* *= ['sort_by', 'page', 'size', 'logical_operator', 'scope_workspace', 'scope_type', 'stack_id']*

#### connector_id *: UUID | str | None*

#### created *: datetime | str | None*

#### flavor *: str | None*

#### generate_filter(table: Type[SQLModel]) → ColumnElement[bool]

Generate the filter for the query.

Stack components can be scoped by type to narrow the search.

Args:
: table: The Table that is being queried from.

Returns:
: The filter expression for the query.

#### id *: UUID | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'connector_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Connector linked to the stack component', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'flavor': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Flavor of the stack component'), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Name of the stack component'), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'scope_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The type to scope this query to.'), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'stack_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Stack of the stack component', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Type of the stack component'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'user_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='User of the stack component', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'workspace_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Workspace of the stack component', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str | None*

#### page *: int*

#### scope_type *: str | None*

#### scope_workspace *: UUID | None*

#### set_scope_type(component_type: str) → None

Set the type of component on which to perform the filtering to scope the response.

Args:
: component_type: The type of component to scope the query to.

#### size *: int*

#### sort_by *: str*

#### stack_id *: UUID | str | None*

#### type *: str | None*

#### updated *: datetime | str | None*

#### user_id *: UUID | str | None*

#### workspace_id *: UUID | str | None*

### *class* zenml.models.v2.core.component.ComponentRequest(\*, user: UUID, workspace: UUID, name: Annotated[str, MaxLen(max_length=255)], type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), flavor: Annotated[str, MaxLen(max_length=255)], configuration: Dict[str, Any], connector_resource_id: str | None = None, labels: Dict[str, Any] | None = None, component_spec_path: str | None = None, connector: UUID | None = None)

Bases: [`ComponentBase`](#zenml.models.v2.core.component.ComponentBase), [`WorkspaceScopedRequest`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedRequest)

Request model for components.

#### ANALYTICS_FIELDS *: ClassVar[List[str]]* *= ['type', 'flavor']*

#### component_spec_path *: str | None*

#### configuration *: Dict[str, Any]*

#### connector *: UUID | None*

#### connector_resource_id *: str | None*

#### flavor *: str*

#### labels *: Dict[str, Any] | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'component_spec_path': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The path to the component spec used for mlstacks deployments.'), 'configuration': FieldInfo(annotation=Dict[str, Any], required=True, title='The stack component configuration.'), 'connector': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The service connector linked to this stack component.'), 'connector_resource_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The ID of a specific resource instance to gain access to through the connector'), 'flavor': FieldInfo(annotation=str, required=True, title='The flavor of the stack component.', metadata=[MaxLen(max_length=255)]), 'labels': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, title='The stack component labels.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the stack component.', metadata=[MaxLen(max_length=255)]), 'type': FieldInfo(annotation=StackComponentType, required=True, title='The type of the stack component.'), 'user': FieldInfo(annotation=UUID, required=True, title='The id of the user that created this resource.'), 'workspace': FieldInfo(annotation=UUID, required=True, title='The workspace to which this resource belongs.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### *classmethod* name_cant_be_a_secret_reference(name: str) → str

Validator to ensure that the given name is not a secret reference.

Args:
: name: The name to validate.

Returns:
: The name if it is not a secret reference.

Raises:
: ValueError: If the name is a secret reference.

#### type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

#### user *: UUID*

#### workspace *: UUID*

### *class* zenml.models.v2.core.component.ComponentResponse(\*, body: [ComponentResponseBody](#zenml.models.v2.core.component.ComponentResponseBody) | None = None, metadata: [ComponentResponseMetadata](#zenml.models.v2.core.component.ComponentResponseMetadata) | None = None, resources: [ComponentResponseResources](#zenml.models.v2.core.component.ComponentResponseResources) | None = None, id: UUID, permission_denied: bool = False, name: Annotated[str, MaxLen(max_length=255)])

Bases: `WorkspaceScopedResponse[ComponentResponseBody, ComponentResponseMetadata, ComponentResponseResources]`

Response model for components.

#### ANALYTICS_FIELDS *: ClassVar[List[str]]* *= ['type', 'flavor']*

#### body *: 'AnyBody' | None*

#### *property* component_spec_path *: str | None*

The component_spec_path property.

Returns:
: the value of the property.

#### *property* configuration *: Dict[str, Any]*

The configuration property.

Returns:
: the value of the property.

#### *property* connector *: [ServiceConnectorResponse](zenml.models.md#zenml.models.ServiceConnectorResponse) | None*

The connector property.

Returns:
: the value of the property.

#### *property* connector_resource_id *: str | None*

The connector_resource_id property.

Returns:
: the value of the property.

#### *property* flavor *: str*

The flavor property.

Returns:
: the value of the property.

#### get_analytics_metadata() → Dict[str, Any]

Add the component labels to analytics metadata.

Returns:
: Dict of analytics metadata.

#### get_hydrated_version() → [ComponentResponse](#zenml.models.v2.core.component.ComponentResponse)

Get the hydrated version of this component.

Returns:
: an instance of the same entity with the metadata field attached.

#### id *: UUID*

#### *property* integration *: str | None*

The integration property.

Returns:
: the value of the property.

#### *property* labels *: Dict[str, Any] | None*

The labels property.

Returns:
: the value of the property.

#### *property* logo_url *: str | None*

The logo_url property.

Returns:
: the value of the property.

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[ComponentResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[ComponentResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the stack component.', metadata=[MaxLen(max_length=255)]), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[ComponentResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str*

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

The type property.

Returns:
: the value of the property.

### *class* zenml.models.v2.core.component.ComponentResponseBody(\*, created: datetime, updated: datetime, user: [UserResponse](#zenml.models.v2.core.user.UserResponse) | None = None, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), flavor: Annotated[str, MaxLen(max_length=255)], integration: Annotated[str | None, MaxLen(max_length=255)] = None, logo_url: str | None = None)

Bases: [`WorkspaceScopedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseBody)

Response body for components.

#### created *: datetime*

#### flavor *: str*

#### integration *: str | None*

#### logo_url *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'flavor': FieldInfo(annotation=str, required=True, title='The flavor of the stack component.', metadata=[MaxLen(max_length=255)]), 'integration': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title="The name of the integration that the component's flavor belongs to.", metadata=[MaxLen(max_length=255)]), 'logo_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Optionally, a url pointing to a png,svg or jpg can be attached.'), 'type': FieldInfo(annotation=StackComponentType, required=True, title='The type of the stack component.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.'), 'user': FieldInfo(annotation=Union[UserResponse, NoneType], required=False, default=None, title='The user who created this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

#### updated *: datetime*

#### user *: 'UserResponse' | None*

### *class* zenml.models.v2.core.component.ComponentResponseMetadata(\*, workspace: [WorkspaceResponse](#zenml.models.v2.core.workspace.WorkspaceResponse), configuration: Dict[str, Any], labels: Dict[str, Any] | None = None, component_spec_path: str | None = None, connector_resource_id: str | None = None, connector: [ServiceConnectorResponse](#zenml.models.v2.core.service_connector.ServiceConnectorResponse) | None = None)

Bases: [`WorkspaceScopedResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseMetadata)

Response metadata for components.

#### component_spec_path *: str | None*

#### configuration *: Dict[str, Any]*

#### connector *: [ServiceConnectorResponse](zenml.models.md#zenml.models.ServiceConnectorResponse) | None*

#### connector_resource_id *: str | None*

#### labels *: Dict[str, Any] | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'component_spec_path': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The path to the component spec used for mlstacks deployments.'), 'configuration': FieldInfo(annotation=Dict[str, Any], required=True, title='The stack component configuration.'), 'connector': FieldInfo(annotation=Union[ServiceConnectorResponse, NoneType], required=False, default=None, title='The service connector linked to this stack component.'), 'connector_resource_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The ID of a specific resource instance to gain access to through the connector'), 'labels': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, title='The stack component labels.'), 'workspace': FieldInfo(annotation=WorkspaceResponse, required=True, title='The workspace of this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

### *class* zenml.models.v2.core.component.ComponentResponseResources(\*\*extra_data: Any)

Bases: [`WorkspaceScopedResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseResources)

Class for all resource models associated with the component entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.component.ComponentUpdate(\*, name: Annotated[str | None, MaxLen(max_length=255)] = None, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType) | None = None, flavor: Annotated[str | None, MaxLen(max_length=255)] = None, configuration: Dict[str, Any] | None = None, connector_resource_id: str | None = None, labels: Dict[str, Any] | None = None, component_spec_path: str | None = None, connector: UUID | None = None)

Bases: [`BaseUpdate`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseUpdate)

Update model for stack components.

#### ANALYTICS_FIELDS *: ClassVar[List[str]]* *= ['type', 'flavor']*

#### component_spec_path *: str | None*

#### configuration *: Dict[str, Any] | None*

#### connector *: UUID | None*

#### connector_resource_id *: str | None*

#### flavor *: str | None*

#### labels *: Dict[str, Any] | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'component_spec_path': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The path to the component spec used for mlstacks deployments.'), 'configuration': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, title='The stack component configuration.'), 'connector': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The service connector linked to this stack component.'), 'connector_resource_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The ID of a specific resource instance to gain access to through the connector'), 'flavor': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The flavor of the stack component.', metadata=[MaxLen(max_length=255)]), 'labels': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, title='The stack component labels.'), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The name of the stack component.', metadata=[MaxLen(max_length=255)]), 'type': FieldInfo(annotation=Union[StackComponentType, NoneType], required=False, default=None, title='The type of the stack component.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

#### type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType) | None*

### *class* zenml.models.v2.core.component.InternalComponentRequest(\*, user: UUID | None = None, workspace: UUID, name: Annotated[str, MaxLen(max_length=255)], type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), flavor: Annotated[str, MaxLen(max_length=255)], configuration: Dict[str, Any], connector_resource_id: str | None = None, labels: Dict[str, Any] | None = None, component_spec_path: str | None = None, connector: UUID | None = None)

Bases: [`ComponentRequest`](#zenml.models.v2.core.component.ComponentRequest)

Internal component request model.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'component_spec_path': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The path to the component spec used for mlstacks deployments.'), 'configuration': FieldInfo(annotation=Dict[str, Any], required=True, title='The stack component configuration.'), 'connector': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The service connector linked to this stack component.'), 'connector_resource_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The ID of a specific resource instance to gain access to through the connector'), 'flavor': FieldInfo(annotation=str, required=True, title='The flavor of the stack component.', metadata=[MaxLen(max_length=255)]), 'labels': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, title='The stack component labels.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the stack component.', metadata=[MaxLen(max_length=255)]), 'type': FieldInfo(annotation=StackComponentType, required=True, title='The type of the stack component.'), 'user': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The id of the user that created this resource.'), 'workspace': FieldInfo(annotation=UUID, required=True, title='The workspace to which this resource belongs.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### user *: UUID | None*

## zenml.models.v2.core.device module

Models representing devices.

### *class* zenml.models.v2.core.device.OAuthDeviceFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_user: UUID | None = None, expires: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, client_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, status: Annotated[[OAuthDeviceStatus](zenml.md#zenml.enums.OAuthDeviceStatus) | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, trusted_device: Annotated[bool | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, failed_auth_attempts: Annotated[int | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, last_login: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None)

Bases: [`UserScopedFilter`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.UserScopedFilter)

Model to enable advanced filtering of OAuth2 devices.

#### client_id *: UUID | str | None*

#### created *: datetime | str | None*

#### expires *: datetime | str | None*

#### failed_auth_attempts *: int | str | None*

#### id *: UUID | str | None*

#### last_login *: datetime | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'client_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='The client ID of the OAuth2 device.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'expires': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='The expiration date of the OAuth2 device.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'failed_auth_attempts': FieldInfo(annotation=Union[int, str, NoneType], required=False, default=None, description='The number of failed authentication attempts.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'last_login': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='The date of the last successful login.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'scope_user': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The user to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'status': FieldInfo(annotation=Union[OAuthDeviceStatus, str, NoneType], required=False, default=None, description='The status of the OAuth2 device.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'trusted_device': FieldInfo(annotation=Union[bool, str, NoneType], required=False, default=None, description='Whether the OAuth2 device was marked as trusted.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### page *: int*

#### scope_user *: UUID | None*

#### size *: int*

#### sort_by *: str*

#### status *: [OAuthDeviceStatus](zenml.md#zenml.enums.OAuthDeviceStatus) | str | None*

#### trusted_device *: bool | str | None*

#### updated *: datetime | str | None*

### *class* zenml.models.v2.core.device.OAuthDeviceInternalRequest(\*, client_id: UUID, expires_in: int, os: str | None = None, ip_address: str | None = None, hostname: str | None = None, python_version: str | None = None, zenml_version: str | None = None, city: str | None = None, region: str | None = None, country: str | None = None)

Bases: [`BaseRequest`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseRequest)

Internal request model for OAuth2 devices.

#### city *: str | None*

#### client_id *: UUID*

#### country *: str | None*

#### expires_in *: int*

#### hostname *: str | None*

#### ip_address *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'city': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The city where the device is located.'), 'client_id': FieldInfo(annotation=UUID, required=True, description='The client ID of the OAuth2 device.'), 'country': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The country where the device is located.'), 'expires_in': FieldInfo(annotation=int, required=True, description='The number of seconds after which the OAuth2 device expires and can no longer be used for authentication.'), 'hostname': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The hostname of the device used for authentication.'), 'ip_address': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The IP address of the device used for authentication.'), 'os': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The operating system of the device used for authentication.'), 'python_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The Python version of the device used for authentication.'), 'region': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The region where the device is located.'), 'zenml_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The ZenML version of the device used for authentication.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### os *: str | None*

#### python_version *: str | None*

#### region *: str | None*

#### zenml_version *: str | None*

### *class* zenml.models.v2.core.device.OAuthDeviceInternalResponse(\*, body: [OAuthDeviceResponseBody](#zenml.models.v2.core.device.OAuthDeviceResponseBody) | None = None, metadata: [OAuthDeviceResponseMetadata](#zenml.models.v2.core.device.OAuthDeviceResponseMetadata) | None = None, resources: [OAuthDeviceResponseResources](#zenml.models.v2.core.device.OAuthDeviceResponseResources) | None = None, id: UUID, permission_denied: bool = False, user_code: str, device_code: str)

Bases: [`OAuthDeviceResponse`](#zenml.models.v2.core.device.OAuthDeviceResponse)

OAuth2 device response model used internally for authentication.

#### body *: 'AnyBody' | None*

#### device_code *: str*

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[OAuthDeviceResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'device_code': FieldInfo(annotation=str, required=True, title='The device code.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[OAuthDeviceResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[OAuthDeviceResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.'), 'user_code': FieldInfo(annotation=str, required=True, title='The user code.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### user_code *: str*

#### verify_device_code(device_code: str) → bool

Verifies a given device code against the stored (hashed) device code.

Args:
: device_code: The device code to verify.

Returns:
: True if the device code is valid, False otherwise.

#### verify_user_code(user_code: str) → bool

Verifies a given user code against the stored (hashed) user code.

Args:
: user_code: The user code to verify.

Returns:
: True if the user code is valid, False otherwise.

### *class* zenml.models.v2.core.device.OAuthDeviceInternalUpdate(\*, locked: bool | None = None, user_id: UUID | None = None, status: [OAuthDeviceStatus](zenml.md#zenml.enums.OAuthDeviceStatus) | None = None, expires_in: int | None = None, failed_auth_attempts: int | None = None, trusted_device: bool | None = None, update_last_login: bool = False, generate_new_codes: bool = False, os: str | None = None, ip_address: str | None = None, hostname: str | None = None, python_version: str | None = None, zenml_version: str | None = None, city: str | None = None, region: str | None = None, country: str | None = None)

Bases: [`OAuthDeviceUpdate`](#zenml.models.v2.core.device.OAuthDeviceUpdate)

OAuth2 device update model used internally for authentication.

#### city *: str | None*

#### country *: str | None*

#### expires_in *: int | None*

#### failed_auth_attempts *: int | None*

#### generate_new_codes *: bool*

#### hostname *: str | None*

#### ip_address *: str | None*

#### locked *: bool | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'city': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The city where the device is located.'), 'country': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The country where the device is located.'), 'expires_in': FieldInfo(annotation=Union[int, NoneType], required=False, default=None, description='Set the device to expire in the given number of seconds. If the value is 0 or negative, the device is set to never expire.'), 'failed_auth_attempts': FieldInfo(annotation=Union[int, NoneType], required=False, default=None, description='Set the number of failed authentication attempts.'), 'generate_new_codes': FieldInfo(annotation=bool, required=False, default=False, description='Whether to generate new user and device codes.'), 'hostname': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The hostname of the device used for authentication.'), 'ip_address': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The IP address of the device used for authentication.'), 'locked': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, description='Whether to lock or unlock the OAuth2 device. A locked device cannot be used for authentication.'), 'os': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The operating system of the device used for authentication.'), 'python_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The Python version of the device used for authentication.'), 'region': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The region where the device is located.'), 'status': FieldInfo(annotation=Union[OAuthDeviceStatus, NoneType], required=False, default=None, description='The new status of the OAuth2 device.'), 'trusted_device': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, description='Whether to mark the OAuth2 device as trusted. A trusted device has a much longer validity time.'), 'update_last_login': FieldInfo(annotation=bool, required=False, default=False, description='Whether to update the last login date.'), 'user_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='User that owns the OAuth2 device.'), 'zenml_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The ZenML version of the device used for authentication.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### os *: str | None*

#### python_version *: str | None*

#### region *: str | None*

#### status *: [OAuthDeviceStatus](zenml.md#zenml.enums.OAuthDeviceStatus) | None*

#### trusted_device *: bool | None*

#### update_last_login *: bool*

#### user_id *: UUID | None*

#### zenml_version *: str | None*

### *class* zenml.models.v2.core.device.OAuthDeviceResponse(\*, body: [OAuthDeviceResponseBody](#zenml.models.v2.core.device.OAuthDeviceResponseBody) | None = None, metadata: [OAuthDeviceResponseMetadata](#zenml.models.v2.core.device.OAuthDeviceResponseMetadata) | None = None, resources: [OAuthDeviceResponseResources](#zenml.models.v2.core.device.OAuthDeviceResponseResources) | None = None, id: UUID, permission_denied: bool = False)

Bases: `UserScopedResponse[OAuthDeviceResponseBody, OAuthDeviceResponseMetadata, OAuthDeviceResponseResources]`

Response model for OAuth2 devices.

#### body *: 'AnyBody' | None*

#### *property* city *: str | None*

The city property.

Returns:
: the value of the property.

#### *property* client_id *: UUID*

The client_id property.

Returns:
: the value of the property.

#### *property* country *: str | None*

The country property.

Returns:
: the value of the property.

#### *property* expires *: datetime | None*

The expires property.

Returns:
: the value of the property.

#### *property* failed_auth_attempts *: int*

The failed_auth_attempts property.

Returns:
: the value of the property.

#### get_hydrated_version() → [OAuthDeviceResponse](#zenml.models.v2.core.device.OAuthDeviceResponse)

Get the hydrated version of this OAuth2 device.

Returns:
: an instance of the same entity with the metadata field attached.

#### *property* hostname *: str | None*

The hostname property.

Returns:
: the value of the property.

#### id *: UUID*

#### *property* ip_address *: str | None*

The ip_address property.

Returns:
: the value of the property.

#### *property* last_login *: datetime | None*

The last_login property.

Returns:
: the value of the property.

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[OAuthDeviceResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[OAuthDeviceResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[OAuthDeviceResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### *property* os *: str | None*

The os property.

Returns:
: the value of the property.

#### permission_denied *: bool*

#### *property* python_version *: str | None*

The python_version property.

Returns:
: the value of the property.

#### *property* region *: str | None*

The region property.

Returns:
: the value of the property.

#### resources *: 'AnyResources' | None*

#### *property* status *: [OAuthDeviceStatus](zenml.md#zenml.enums.OAuthDeviceStatus)*

The status property.

Returns:
: the value of the property.

#### *property* trusted_device *: bool*

The trusted_device property.

Returns:
: the value of the property.

#### *property* zenml_version *: str | None*

The zenml_version property.

Returns:
: the value of the property.

### *class* zenml.models.v2.core.device.OAuthDeviceResponseBody(\*, created: datetime, updated: datetime, user: [UserResponse](#zenml.models.v2.core.user.UserResponse) | None = None, client_id: UUID, expires: datetime | None = None, trusted_device: bool, status: [OAuthDeviceStatus](zenml.md#zenml.enums.OAuthDeviceStatus), os: str | None = None, ip_address: str | None = None, hostname: str | None = None)

Bases: [`UserScopedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.UserScopedResponseBody)

Response body for OAuth2 devices.

#### client_id *: UUID*

#### created *: datetime*

#### expires *: datetime | None*

#### hostname *: str | None*

#### ip_address *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'client_id': FieldInfo(annotation=UUID, required=True, description='The client ID of the OAuth2 device.'), 'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'expires': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None, description='The expiration date of the OAuth2 device after which the device is no longer valid and cannot be used for authentication.'), 'hostname': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The hostname of the device used for authentication.'), 'ip_address': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The IP address of the device used for authentication.'), 'os': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The operating system of the device used for authentication.'), 'status': FieldInfo(annotation=OAuthDeviceStatus, required=True, description='The status of the OAuth2 device.'), 'trusted_device': FieldInfo(annotation=bool, required=True, description='Whether the OAuth2 device was marked as trusted. A trusted device has a much longer validity time.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.'), 'user': FieldInfo(annotation=Union[UserResponse, NoneType], required=False, default=None, title='The user who created this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### os *: str | None*

#### status *: [OAuthDeviceStatus](zenml.md#zenml.enums.OAuthDeviceStatus)*

#### trusted_device *: bool*

#### updated *: datetime*

#### user *: 'UserResponse' | None*

### *class* zenml.models.v2.core.device.OAuthDeviceResponseMetadata(\*, python_version: str | None = None, zenml_version: str | None = None, city: str | None = None, region: str | None = None, country: str | None = None, failed_auth_attempts: int, last_login: datetime | None)

Bases: [`UserScopedResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.UserScopedResponseMetadata)

Response metadata for OAuth2 devices.

#### city *: str | None*

#### country *: str | None*

#### failed_auth_attempts *: int*

#### last_login *: datetime | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'city': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The city where the device is located.'), 'country': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The country where the device is located.'), 'failed_auth_attempts': FieldInfo(annotation=int, required=True, description='The number of failed authentication attempts.'), 'last_login': FieldInfo(annotation=Union[datetime, NoneType], required=True, description='The date of the last successful login.'), 'python_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The Python version of the device used for authentication.'), 'region': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The region where the device is located.'), 'zenml_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The ZenML version of the device used for authentication.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### python_version *: str | None*

#### region *: str | None*

#### zenml_version *: str | None*

### *class* zenml.models.v2.core.device.OAuthDeviceResponseResources(\*\*extra_data: Any)

Bases: [`UserScopedResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.UserScopedResponseResources)

Class for all resource models associated with the OAuthDevice entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.device.OAuthDeviceUpdate(\*, locked: bool | None = None)

Bases: `BaseModel`

OAuth2 device update model.

#### locked *: bool | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'locked': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, description='Whether to lock or unlock the OAuth2 device. A locked device cannot be used for authentication.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## zenml.models.v2.core.event_source module

Collection of all models concerning event configurations.

### *class* zenml.models.v2.core.event_source.EventSourceFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None, name: str | None = None, flavor: str | None = None, plugin_subtype: Annotated[str | None, MaxLen(max_length=255)] = None)

Bases: [`WorkspaceScopedFilter`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedFilter)

Model to enable advanced filtering of all EventSourceModels.

#### created *: datetime | str | None*

#### flavor *: str | None*

#### id *: UUID | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'flavor': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Flavor of the event source'), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Name of the event source'), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'plugin_subtype': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The plugin sub type of the event source.', metadata=[MaxLen(max_length=255)]), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str | None*

#### page *: int*

#### plugin_subtype *: str | None*

#### scope_workspace *: UUID | None*

#### size *: int*

#### sort_by *: str*

#### updated *: datetime | str | None*

### *class* zenml.models.v2.core.event_source.EventSourceRequest(\*, user: UUID, workspace: UUID, name: Annotated[str, MaxLen(max_length=255)], flavor: Annotated[str, MaxLen(max_length=255)], plugin_subtype: [PluginSubType](zenml.md#zenml.enums.PluginSubType), description: Annotated[str, MaxLen(max_length=255)] = '', configuration: Dict[str, Any])

Bases: [`WorkspaceScopedRequest`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedRequest)

BaseModel for all event sources.

#### configuration *: Dict[str, Any]*

#### description *: str*

#### flavor *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'configuration': FieldInfo(annotation=Dict[str, Any], required=True, title='The event source configuration.'), 'description': FieldInfo(annotation=str, required=False, default='', title='The description of the event source.', metadata=[MaxLen(max_length=255)]), 'flavor': FieldInfo(annotation=str, required=True, title='The flavor of event source.', metadata=[MaxLen(max_length=255)]), 'name': FieldInfo(annotation=str, required=True, title='The name of the event source.', metadata=[MaxLen(max_length=255)]), 'plugin_subtype': FieldInfo(annotation=PluginSubType, required=True, title='The plugin subtype of the event source.'), 'user': FieldInfo(annotation=UUID, required=True, title='The id of the user that created this resource.'), 'workspace': FieldInfo(annotation=UUID, required=True, title='The workspace to which this resource belongs.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### plugin_subtype *: [PluginSubType](zenml.md#zenml.enums.PluginSubType)*

#### user *: UUID*

#### workspace *: UUID*

### *class* zenml.models.v2.core.event_source.EventSourceResponse(\*, body: [EventSourceResponseBody](#zenml.models.v2.core.event_source.EventSourceResponseBody) | None = None, metadata: [EventSourceResponseMetadata](#zenml.models.v2.core.event_source.EventSourceResponseMetadata) | None = None, resources: [EventSourceResponseResources](#zenml.models.v2.core.event_source.EventSourceResponseResources) | None = None, id: UUID, permission_denied: bool = False, name: Annotated[str, MaxLen(max_length=255)])

Bases: `WorkspaceScopedResponse[EventSourceResponseBody, EventSourceResponseMetadata, EventSourceResponseResources]`

Response model for event sources.

#### body *: 'AnyBody' | None*

#### *property* configuration *: Dict[str, Any]*

The configuration property.

Returns:
: the value of the property.

#### *property* description *: str*

The description property.

Returns:
: the value of the property.

#### *property* flavor *: str*

The flavor property.

Returns:
: the value of the property.

#### get_hydrated_version() → [EventSourceResponse](#zenml.models.v2.core.event_source.EventSourceResponse)

Get the hydrated version of this event source.

Returns:
: An instance of the same entity with the metadata field attached.

#### id *: UUID*

#### *property* is_active *: bool*

The is_active property.

Returns:
: the value of the property.

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[EventSourceResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[EventSourceResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the event source.', metadata=[MaxLen(max_length=255)]), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[EventSourceResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str*

#### permission_denied *: bool*

#### *property* plugin_subtype *: [PluginSubType](zenml.md#zenml.enums.PluginSubType)*

The plugin_subtype property.

Returns:
: the value of the property.

#### resources *: 'AnyResources' | None*

#### set_configuration(configuration: Dict[str, Any]) → None

Set the configuration property.

Args:
: configuration: The value to set.

### *class* zenml.models.v2.core.event_source.EventSourceResponseBody(\*, created: datetime, updated: datetime, user: [UserResponse](#zenml.models.v2.core.user.UserResponse) | None = None, flavor: Annotated[str, MaxLen(max_length=255)], plugin_subtype: [PluginSubType](zenml.md#zenml.enums.PluginSubType), is_active: bool)

Bases: [`WorkspaceScopedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseBody)

ResponseBody for event sources.

#### created *: datetime*

#### flavor *: str*

#### is_active *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'flavor': FieldInfo(annotation=str, required=True, title='The flavor of event source.', metadata=[MaxLen(max_length=255)]), 'is_active': FieldInfo(annotation=bool, required=True, title='Whether the event source is active.'), 'plugin_subtype': FieldInfo(annotation=PluginSubType, required=True, title='The plugin subtype of the event source.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.'), 'user': FieldInfo(annotation=Union[UserResponse, NoneType], required=False, default=None, title='The user who created this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### plugin_subtype *: [PluginSubType](zenml.md#zenml.enums.PluginSubType)*

#### updated *: datetime*

#### user *: 'UserResponse' | None*

### *class* zenml.models.v2.core.event_source.EventSourceResponseMetadata(\*, workspace: [WorkspaceResponse](#zenml.models.v2.core.workspace.WorkspaceResponse), description: Annotated[str, MaxLen(max_length=255)] = '', configuration: Dict[str, Any])

Bases: [`WorkspaceScopedResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseMetadata)

Response metadata for event sources.

#### configuration *: Dict[str, Any]*

#### description *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'configuration': FieldInfo(annotation=Dict[str, Any], required=True, title='The event source configuration.'), 'description': FieldInfo(annotation=str, required=False, default='', title='The description of the event source.', metadata=[MaxLen(max_length=255)]), 'workspace': FieldInfo(annotation=WorkspaceResponse, required=True, title='The workspace of this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

### *class* zenml.models.v2.core.event_source.EventSourceResponseResources(\*, triggers: [Page](zenml.models.v2.base.md#id327)[[TriggerResponse](zenml.models.md#zenml.models.TriggerResponse)], \*\*extra_data: Any)

Bases: [`WorkspaceScopedResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseResources)

Class for all resource models associated with the code repository entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'triggers': FieldInfo(annotation=Page[TriggerResponse], required=True, title='The triggers configured with this event source.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### triggers *: [Page](zenml.models.v2.base.md#id327)[[TriggerResponse](zenml.models.md#zenml.models.TriggerResponse)]*

### *class* zenml.models.v2.core.event_source.EventSourceUpdate(\*, name: Annotated[str | None, MaxLen(max_length=255)] = None, description: Annotated[str | None, MaxLen(max_length=255)] = None, configuration: Dict[str, Any] | None = None, is_active: bool | None = None)

Bases: [`BaseZenModel`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseZenModel)

Update model for event sources.

#### configuration *: Dict[str, Any] | None*

#### description *: str | None*

#### *classmethod* from_response(response: [EventSourceResponse](#zenml.models.v2.core.event_source.EventSourceResponse)) → [EventSourceUpdate](#zenml.models.v2.core.event_source.EventSourceUpdate)

Create an update model from a response model.

Args:
: response: The response model to create the update model from.

Returns:
: The update model.

#### is_active *: bool | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'configuration': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, title='The updated event source configuration.'), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The updated description of the event source.', metadata=[MaxLen(max_length=255)]), 'is_active': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, title='The status of the event source.'), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The updated name of the event source.', metadata=[MaxLen(max_length=255)])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

## zenml.models.v2.core.event_source_flavor module

Models representing event source flavors..

### *class* zenml.models.v2.core.event_source_flavor.EventSourceFlavorResponse(\*, body: [EventSourceFlavorResponseBody](#zenml.models.v2.core.event_source_flavor.EventSourceFlavorResponseBody) | None = None, metadata: [EventSourceFlavorResponseMetadata](#zenml.models.v2.core.event_source_flavor.EventSourceFlavorResponseMetadata) | None = None, resources: [EventSourceFlavorResponseResources](#zenml.models.v2.core.event_source_flavor.EventSourceFlavorResponseResources) | None = None, name: str, type: [PluginType](zenml.md#zenml.enums.PluginType), subtype: [PluginSubType](zenml.md#zenml.enums.PluginSubType))

Bases: `BasePluginFlavorResponse[EventSourceFlavorResponseBody, EventSourceFlavorResponseMetadata, EventSourceFlavorResponseResources]`

Response model for Event Source Flavors.

#### body *: 'AnyBody' | None*

#### *property* filter_config_schema *: Dict[str, Any]*

The filter_config_schema property.

Returns:
: the value of the property.

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[EventSourceFlavorResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'metadata': FieldInfo(annotation=Union[EventSourceFlavorResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='Name of the flavor.'), 'resources': FieldInfo(annotation=Union[EventSourceFlavorResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.'), 'subtype': FieldInfo(annotation=PluginSubType, required=True, title='Subtype of the plugin.'), 'type': FieldInfo(annotation=PluginType, required=True, title='Type of the plugin.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str*

#### resources *: 'AnyResources' | None*

#### *property* source_config_schema *: Dict[str, Any]*

The source_config_schema property.

Returns:
: the value of the property.

#### subtype *: [PluginSubType](zenml.md#zenml.enums.PluginSubType)*

#### type *: [PluginType](zenml.md#zenml.enums.PluginType)*

### *class* zenml.models.v2.core.event_source_flavor.EventSourceFlavorResponseBody

Bases: [`BasePluginResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.base_plugin_flavor.BasePluginResponseBody)

Response body for event flavors.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.event_source_flavor.EventSourceFlavorResponseMetadata(\*, source_config_schema: Dict[str, Any], filter_config_schema: Dict[str, Any])

Bases: [`BasePluginResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.base_plugin_flavor.BasePluginResponseMetadata)

Response metadata for event flavors.

#### filter_config_schema *: Dict[str, Any]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'filter_config_schema': FieldInfo(annotation=Dict[str, Any], required=True), 'source_config_schema': FieldInfo(annotation=Dict[str, Any], required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### source_config_schema *: Dict[str, Any]*

### *class* zenml.models.v2.core.event_source_flavor.EventSourceFlavorResponseResources(\*\*extra_data: Any)

Bases: [`BasePluginResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.base_plugin_flavor.BasePluginResponseResources)

Response resources for event source flavors.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## zenml.models.v2.core.flavor module

Models representing flavors.

### *class* zenml.models.v2.core.flavor.FlavorFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None, name: str | None = None, type: str | None = None, integration: str | None = None, workspace_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, user_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None)

Bases: [`WorkspaceScopedFilter`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedFilter)

Model to enable advanced filtering of all Flavors.

#### created *: datetime | str | None*

#### id *: UUID | str | None*

#### integration *: str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'integration': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Integration associated with the flavor'), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Name of the flavor'), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Stack Component Type of the stack flavor'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'user_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='User of the stack', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'workspace_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Workspace of the stack', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str | None*

#### page *: int*

#### scope_workspace *: UUID | None*

#### size *: int*

#### sort_by *: str*

#### type *: str | None*

#### updated *: datetime | str | None*

#### user_id *: UUID | str | None*

#### workspace_id *: UUID | str | None*

### *class* zenml.models.v2.core.flavor.FlavorRequest(\*, user: UUID, name: Annotated[str, MaxLen(max_length=255)], type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), config_schema: Dict[str, Any], connector_type: Annotated[str | None, MaxLen(max_length=255)] = None, connector_resource_type: Annotated[str | None, MaxLen(max_length=255)] = None, connector_resource_id_attr: Annotated[str | None, MaxLen(max_length=255)] = None, source: Annotated[str, MaxLen(max_length=255)], integration: Annotated[str | None, MaxLen(max_length=255)], logo_url: str | None = None, docs_url: str | None = None, sdk_docs_url: str | None = None, is_custom: bool = True, workspace: UUID | None = None)

Bases: [`UserScopedRequest`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.UserScopedRequest)

Request model for flavors.

#### ANALYTICS_FIELDS *: ClassVar[List[str]]* *= ['type', 'integration']*

#### config_schema *: Dict[str, Any]*

#### connector_resource_id_attr *: str | None*

#### connector_resource_type *: str | None*

#### connector_type *: str | None*

#### docs_url *: str | None*

#### integration *: str | None*

#### is_custom *: bool*

#### logo_url *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config_schema': FieldInfo(annotation=Dict[str, Any], required=True, title="The JSON schema of this flavor's corresponding configuration."), 'connector_resource_id_attr': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The name of an attribute in the stack component configuration that plays the role of resource ID when linked to a service connector.', metadata=[MaxLen(max_length=255)]), 'connector_resource_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The resource type of the connector that this flavor uses.', metadata=[MaxLen(max_length=255)]), 'connector_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The type of the connector that this flavor uses.', metadata=[MaxLen(max_length=255)]), 'docs_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Optionally, a url pointing to docs, within docs.zenml.io.'), 'integration': FieldInfo(annotation=Union[str, NoneType], required=True, title='The name of the integration that the Flavor belongs to.', metadata=[MaxLen(max_length=255)]), 'is_custom': FieldInfo(annotation=bool, required=False, default=True, title='Whether or not this flavor is a custom, user created flavor.'), 'logo_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Optionally, a url pointing to a png,svg or jpg can be attached.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the Flavor.', metadata=[MaxLen(max_length=255)]), 'sdk_docs_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Optionally, a url pointing to SDK docs,within sdkdocs.zenml.io.'), 'source': FieldInfo(annotation=str, required=True, title='The path to the module which contains this Flavor.', metadata=[MaxLen(max_length=255)]), 'type': FieldInfo(annotation=StackComponentType, required=True, title='The type of the Flavor.'), 'user': FieldInfo(annotation=UUID, required=True, title='The id of the user that created this resource.'), 'workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The workspace to which this resource belongs.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### sdk_docs_url *: str | None*

#### source *: str*

#### type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

#### user *: UUID*

#### workspace *: UUID | None*

### *class* zenml.models.v2.core.flavor.FlavorResponse(\*, body: [FlavorResponseBody](#zenml.models.v2.core.flavor.FlavorResponseBody) | None = None, metadata: [FlavorResponseMetadata](#zenml.models.v2.core.flavor.FlavorResponseMetadata) | None = None, resources: [FlavorResponseResources](#zenml.models.v2.core.flavor.FlavorResponseResources) | None = None, id: UUID, permission_denied: bool = False, name: Annotated[str, MaxLen(max_length=255)])

Bases: `UserScopedResponse[FlavorResponseBody, FlavorResponseMetadata, FlavorResponseResources]`

Response model for flavors.

#### ANALYTICS_FIELDS *: ClassVar[List[str]]* *= ['id', 'type', 'integration']*

#### body *: 'AnyBody' | None*

#### *property* config_schema *: Dict[str, Any]*

The config_schema property.

Returns:
: the value of the property.

#### *property* connector_requirements *: [ServiceConnectorRequirements](zenml.models.md#zenml.models.ServiceConnectorRequirements) | None*

Returns the connector requirements for the flavor.

Returns:
: The connector requirements for the flavor.

#### *property* connector_resource_id_attr *: str | None*

The connector_resource_id_attr property.

Returns:
: the value of the property.

#### *property* connector_resource_type *: str | None*

The connector_resource_type property.

Returns:
: the value of the property.

#### *property* connector_type *: str | None*

The connector_type property.

Returns:
: the value of the property.

#### *property* docs_url *: str | None*

The docs_url property.

Returns:
: the value of the property.

#### get_hydrated_version() → [FlavorResponse](#zenml.models.v2.core.flavor.FlavorResponse)

Get the hydrated version of the flavor.

Returns:
: an instance of the same entity with the metadata field attached.

#### id *: UUID*

#### *property* integration *: str | None*

The integration property.

Returns:
: the value of the property.

#### *property* is_custom *: bool*

The is_custom property.

Returns:
: the value of the property.

#### *property* logo_url *: str | None*

The logo_url property.

Returns:
: the value of the property.

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[FlavorResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[FlavorResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the Flavor.', metadata=[MaxLen(max_length=255)]), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[FlavorResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str*

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* sdk_docs_url *: str | None*

The sdk_docs_url property.

Returns:
: the value of the property.

#### *property* source *: str*

The source property.

Returns:
: the value of the property.

#### *property* type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

The type property.

Returns:
: the value of the property.

#### *property* workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse) | None*

The workspace property.

Returns:
: the value of the property.

### *class* zenml.models.v2.core.flavor.FlavorResponseBody(\*, created: datetime, updated: datetime, user: [UserResponse](#zenml.models.v2.core.user.UserResponse) | None = None, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), integration: Annotated[str | None, MaxLen(max_length=255)], logo_url: str | None = None)

Bases: [`UserScopedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.UserScopedResponseBody)

Response body for flavor.

#### created *: datetime*

#### integration *: str | None*

#### logo_url *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'integration': FieldInfo(annotation=Union[str, NoneType], required=True, title='The name of the integration that the Flavor belongs to.', metadata=[MaxLen(max_length=255)]), 'logo_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Optionally, a url pointing to a png,svg or jpg can be attached.'), 'type': FieldInfo(annotation=StackComponentType, required=True, title='The type of the Flavor.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.'), 'user': FieldInfo(annotation=Union[UserResponse, NoneType], required=False, default=None, title='The user who created this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

#### updated *: datetime*

#### user *: 'UserResponse' | None*

### *class* zenml.models.v2.core.flavor.FlavorResponseMetadata(\*, workspace: [WorkspaceResponse](#zenml.models.v2.core.workspace.WorkspaceResponse) | None, config_schema: Dict[str, Any], connector_type: Annotated[str | None, MaxLen(max_length=255)] = None, connector_resource_type: Annotated[str | None, MaxLen(max_length=255)] = None, connector_resource_id_attr: Annotated[str | None, MaxLen(max_length=255)] = None, source: Annotated[str, MaxLen(max_length=255)], docs_url: str | None = None, sdk_docs_url: str | None = None, is_custom: bool = True)

Bases: [`UserScopedResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.UserScopedResponseMetadata)

Response metadata for flavors.

#### config_schema *: Dict[str, Any]*

#### connector_resource_id_attr *: str | None*

#### connector_resource_type *: str | None*

#### connector_type *: str | None*

#### docs_url *: str | None*

#### is_custom *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config_schema': FieldInfo(annotation=Dict[str, Any], required=True, title="The JSON schema of this flavor's corresponding configuration."), 'connector_resource_id_attr': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The name of an attribute in the stack component configuration that plays the role of resource ID when linked to a service connector.', metadata=[MaxLen(max_length=255)]), 'connector_resource_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The resource type of the connector that this flavor uses.', metadata=[MaxLen(max_length=255)]), 'connector_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The type of the connector that this flavor uses.', metadata=[MaxLen(max_length=255)]), 'docs_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Optionally, a url pointing to docs, within docs.zenml.io.'), 'is_custom': FieldInfo(annotation=bool, required=False, default=True, title='Whether or not this flavor is a custom, user created flavor.'), 'sdk_docs_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Optionally, a url pointing to SDK docs,within sdkdocs.zenml.io.'), 'source': FieldInfo(annotation=str, required=True, title='The path to the module which contains this Flavor.', metadata=[MaxLen(max_length=255)]), 'workspace': FieldInfo(annotation=Union[WorkspaceResponse, NoneType], required=True, title='The project of this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### sdk_docs_url *: str | None*

#### source *: str*

#### workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse) | None*

### *class* zenml.models.v2.core.flavor.FlavorResponseResources(\*\*extra_data: Any)

Bases: [`UserScopedResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.UserScopedResponseResources)

Class for all resource models associated with the flavor entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.flavor.FlavorUpdate(\*, name: Annotated[str | None, MaxLen(max_length=255)] = None, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType) | None = None, config_schema: Dict[str, Any] | None = None, connector_type: Annotated[str | None, MaxLen(max_length=255)] = None, connector_resource_type: Annotated[str | None, MaxLen(max_length=255)] = None, connector_resource_id_attr: Annotated[str | None, MaxLen(max_length=255)] = None, source: Annotated[str | None, MaxLen(max_length=255)] = None, integration: Annotated[str | None, MaxLen(max_length=255)] = None, logo_url: str | None = None, docs_url: str | None = None, sdk_docs_url: str | None = None, is_custom: bool | None = None, workspace: UUID | None = None)

Bases: [`BaseUpdate`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseUpdate)

Update model for flavors.

#### config_schema *: Dict[str, Any] | None*

#### connector_resource_id_attr *: str | None*

#### connector_resource_type *: str | None*

#### connector_type *: str | None*

#### docs_url *: str | None*

#### integration *: str | None*

#### is_custom *: bool | None*

#### logo_url *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config_schema': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, title="The JSON schema of this flavor's corresponding configuration."), 'connector_resource_id_attr': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The name of an attribute in the stack component configuration that plays the role of resource ID when linked to a service connector.', metadata=[MaxLen(max_length=255)]), 'connector_resource_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The resource type of the connector that this flavor uses.', metadata=[MaxLen(max_length=255)]), 'connector_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The type of the connector that this flavor uses.', metadata=[MaxLen(max_length=255)]), 'docs_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Optionally, a url pointing to docs, within docs.zenml.io.'), 'integration': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The name of the integration that the Flavor belongs to.', metadata=[MaxLen(max_length=255)]), 'is_custom': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, title='Whether or not this flavor is a custom, user created flavor.'), 'logo_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Optionally, a url pointing to a png,svg or jpg can be attached.'), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The name of the Flavor.', metadata=[MaxLen(max_length=255)]), 'sdk_docs_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Optionally, a url pointing to SDK docs,within sdkdocs.zenml.io.'), 'source': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The path to the module which contains this Flavor.', metadata=[MaxLen(max_length=255)]), 'type': FieldInfo(annotation=Union[StackComponentType, NoneType], required=False, default=None, title='The type of the Flavor.'), 'workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The workspace to which this resource belongs.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

#### sdk_docs_url *: str | None*

#### source *: str | None*

#### type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType) | None*

#### workspace *: UUID | None*

### *class* zenml.models.v2.core.flavor.InternalFlavorRequest(\*, user: UUID | None = None, name: Annotated[str, MaxLen(max_length=255)], type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), config_schema: Dict[str, Any], connector_type: Annotated[str | None, MaxLen(max_length=255)] = None, connector_resource_type: Annotated[str | None, MaxLen(max_length=255)] = None, connector_resource_id_attr: Annotated[str | None, MaxLen(max_length=255)] = None, source: Annotated[str, MaxLen(max_length=255)], integration: Annotated[str | None, MaxLen(max_length=255)], logo_url: str | None = None, docs_url: str | None = None, sdk_docs_url: str | None = None, is_custom: bool = True, workspace: UUID | None = None)

Bases: [`FlavorRequest`](#zenml.models.v2.core.flavor.FlavorRequest)

Internal flavor request model.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config_schema': FieldInfo(annotation=Dict[str, Any], required=True, title="The JSON schema of this flavor's corresponding configuration."), 'connector_resource_id_attr': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The name of an attribute in the stack component configuration that plays the role of resource ID when linked to a service connector.', metadata=[MaxLen(max_length=255)]), 'connector_resource_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The resource type of the connector that this flavor uses.', metadata=[MaxLen(max_length=255)]), 'connector_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The type of the connector that this flavor uses.', metadata=[MaxLen(max_length=255)]), 'docs_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Optionally, a url pointing to docs, within docs.zenml.io.'), 'integration': FieldInfo(annotation=Union[str, NoneType], required=True, title='The name of the integration that the Flavor belongs to.', metadata=[MaxLen(max_length=255)]), 'is_custom': FieldInfo(annotation=bool, required=False, default=True, title='Whether or not this flavor is a custom, user created flavor.'), 'logo_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Optionally, a url pointing to a png,svg or jpg can be attached.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the Flavor.', metadata=[MaxLen(max_length=255)]), 'sdk_docs_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Optionally, a url pointing to SDK docs,within sdkdocs.zenml.io.'), 'source': FieldInfo(annotation=str, required=True, title='The path to the module which contains this Flavor.', metadata=[MaxLen(max_length=255)]), 'type': FieldInfo(annotation=StackComponentType, required=True, title='The type of the Flavor.'), 'user': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The id of the user that created this resource.'), 'workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The workspace to which this resource belongs.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### user *: UUID | None*

## zenml.models.v2.core.logs module

Models representing logs.

### *class* zenml.models.v2.core.logs.LogsRequest(\*, uri: str, artifact_store_id: Annotated[str | UUID, \_PydanticGeneralMetadata(union_mode='left_to_right')])

Bases: [`BaseRequest`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseRequest)

Request model for logs.

#### artifact_store_id *: str | UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact_store_id': FieldInfo(annotation=Union[str, UUID], required=True, title='The artifact store ID to associate the logs with.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'uri': FieldInfo(annotation=str, required=True, title='The uri of the logs file')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### *classmethod* str_field_max_length_check(value: Any) → Any

Checks if the length of the value exceeds the maximum text length.

Args:
: value: the value set in the field

Returns:
: the value itself.

Raises:
: AssertionError: if the length of the field is longer than the
  : maximum threshold.

#### *classmethod* text_field_max_length_check(value: Any) → Any

Checks if the length of the value exceeds the maximum text length.

Args:
: value: the value set in the field

Returns:
: the value itself.

Raises:
: AssertionError: if the length of the field is longer than the
  : maximum threshold.

#### uri *: str*

### *class* zenml.models.v2.core.logs.LogsResponse(\*, body: [LogsResponseBody](#zenml.models.v2.core.logs.LogsResponseBody) | None = None, metadata: [LogsResponseMetadata](#zenml.models.v2.core.logs.LogsResponseMetadata) | None = None, resources: [LogsResponseResources](#zenml.models.v2.core.logs.LogsResponseResources) | None = None, id: UUID, permission_denied: bool = False)

Bases: `BaseIdentifiedResponse[LogsResponseBody, LogsResponseMetadata, LogsResponseResources]`

Response model for logs.

#### *property* artifact_store_id *: str | UUID*

The artifact_store_id property.

Returns:
: the value of the property.

#### body *: 'AnyBody' | None*

#### get_hydrated_version() → [LogsResponse](#zenml.models.v2.core.logs.LogsResponse)

Get the hydrated version of these logs.

Returns:
: an instance of the same entity with the metadata field attached.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[LogsResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[LogsResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[LogsResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### *property* pipeline_run_id *: UUID | str | None*

The pipeline_run_id property.

Returns:
: the value of the property.

#### resources *: 'AnyResources' | None*

#### *property* step_run_id *: UUID | str | None*

The step_run_id property.

Returns:
: the value of the property.

#### *property* uri *: str*

The uri property.

Returns:
: the value of the property.

### *class* zenml.models.v2.core.logs.LogsResponseBody(\*, created: datetime, updated: datetime, uri: Annotated[str, MaxLen(max_length=65535)])

Bases: [`BaseDatedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseDatedResponseBody)

Response body for logs.

#### created *: datetime*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.'), 'uri': FieldInfo(annotation=str, required=True, title='The uri of the logs file', metadata=[MaxLen(max_length=65535)])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### updated *: datetime*

#### uri *: str*

### *class* zenml.models.v2.core.logs.LogsResponseMetadata(\*, step_run_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, pipeline_run_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, artifact_store_id: Annotated[str | UUID, \_PydanticGeneralMetadata(union_mode='left_to_right')])

Bases: [`BaseResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseMetadata)

Response metadata for logs.

#### artifact_store_id *: str | UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact_store_id': FieldInfo(annotation=Union[str, UUID], required=True, title='The artifact store ID to associate the logs with.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'pipeline_run_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, title='Pipeline run ID to associate the logs with.', description='When this is set, step_run_id should be set to None.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'step_run_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, title='Step ID to associate the logs with.', description='When this is set, pipeline_run_id should be set to None.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### pipeline_run_id *: UUID | str | None*

#### step_run_id *: UUID | str | None*

#### *classmethod* str_field_max_length_check(value: Any) → Any

Checks if the length of the value exceeds the maximum text length.

Args:
: value: the value set in the field

Returns:
: the value itself.

Raises:
: AssertionError: if the length of the field is longer than the
  : maximum threshold.

### *class* zenml.models.v2.core.logs.LogsResponseResources(\*\*extra_data: Any)

Bases: [`BaseResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseResources)

Class for all resource models associated with the Logs entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## zenml.models.v2.core.model module

Models representing models.

### *class* zenml.models.v2.core.model.ModelFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None, tag: str | None = None, name: str | None = None, workspace_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, user_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None)

Bases: [`WorkspaceScopedTaggableFilter`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedTaggableFilter)

Model to enable advanced filtering of all Workspaces.

#### CLI_EXCLUDE_FIELDS *: ClassVar[List[str]]* *= ['scope_workspace', 'workspace_id', 'user_id']*

#### created *: datetime | str | None*

#### id *: UUID | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Name of the Model'), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'tag': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Tag to apply to the filter query.'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'user_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='User of the Model', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'workspace_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Workspace of the Model', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str | None*

#### page *: int*

#### scope_workspace *: UUID | None*

#### size *: int*

#### sort_by *: str*

#### tag *: str | None*

#### updated *: datetime | str | None*

#### user_id *: UUID | str | None*

#### workspace_id *: UUID | str | None*

### *class* zenml.models.v2.core.model.ModelRequest(\*, user: UUID, workspace: UUID, name: Annotated[str, MaxLen(max_length=255)], license: Annotated[str | None, MaxLen(max_length=65535)] = None, description: Annotated[str | None, MaxLen(max_length=65535)] = None, audience: Annotated[str | None, MaxLen(max_length=65535)] = None, use_cases: Annotated[str | None, MaxLen(max_length=65535)] = None, limitations: Annotated[str | None, MaxLen(max_length=65535)] = None, trade_offs: Annotated[str | None, MaxLen(max_length=65535)] = None, ethics: Annotated[str | None, MaxLen(max_length=65535)] = None, tags: List[str] | None, save_models_to_registry: bool = True)

Bases: [`WorkspaceScopedRequest`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedRequest)

Request model for models.

#### audience *: str | None*

#### description *: str | None*

#### ethics *: str | None*

#### license *: str | None*

#### limitations *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'audience': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The target audience of the model', metadata=[MaxLen(max_length=65535)]), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The description of the model', metadata=[MaxLen(max_length=65535)]), 'ethics': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The ethical implications of the model', metadata=[MaxLen(max_length=65535)]), 'license': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The license model created under', metadata=[MaxLen(max_length=65535)]), 'limitations': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The know limitations of the model', metadata=[MaxLen(max_length=65535)]), 'name': FieldInfo(annotation=str, required=True, title='The name of the model', metadata=[MaxLen(max_length=255)]), 'save_models_to_registry': FieldInfo(annotation=bool, required=False, default=True, title='Whether to save all ModelArtifacts to Model Registry'), 'tags': FieldInfo(annotation=Union[List[str], NoneType], required=True, title='Tags associated with the model'), 'trade_offs': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The trade offs of the model', metadata=[MaxLen(max_length=65535)]), 'use_cases': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The use cases of the model', metadata=[MaxLen(max_length=65535)]), 'user': FieldInfo(annotation=UUID, required=True, title='The id of the user that created this resource.'), 'workspace': FieldInfo(annotation=UUID, required=True, title='The workspace to which this resource belongs.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### save_models_to_registry *: bool*

#### tags *: List[str] | None*

#### trade_offs *: str | None*

#### use_cases *: str | None*

#### user *: UUID*

#### workspace *: UUID*

### *class* zenml.models.v2.core.model.ModelResponse(\*, body: [ModelResponseBody](#zenml.models.v2.core.model.ModelResponseBody) | None = None, metadata: [ModelResponseMetadata](#zenml.models.v2.core.model.ModelResponseMetadata) | None = None, resources: [ModelResponseResources](#zenml.models.v2.core.model.ModelResponseResources) | None = None, id: UUID, permission_denied: bool = False, name: Annotated[str, MaxLen(max_length=255)])

Bases: `WorkspaceScopedResponse[ModelResponseBody, ModelResponseMetadata, ModelResponseResources]`

Response model for models.

#### *property* audience *: str | None*

The audience property.

Returns:
: the value of the property.

#### body *: 'AnyBody' | None*

#### *property* description *: str | None*

The description property.

Returns:
: the value of the property.

#### *property* ethics *: str | None*

The ethics property.

Returns:
: the value of the property.

#### get_hydrated_version() → [ModelResponse](#zenml.models.v2.core.model.ModelResponse)

Get the hydrated version of this model.

Returns:
: an instance of the same entity with the metadata field attached.

#### id *: UUID*

#### *property* latest_version_id *: UUID | None*

The latest_version_id property.

Returns:
: the value of the property.

#### *property* latest_version_name *: str | None*

The latest_version_name property.

Returns:
: the value of the property.

#### *property* license *: str | None*

The license property.

Returns:
: the value of the property.

#### *property* limitations *: str | None*

The limitations property.

Returns:
: the value of the property.

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[ModelResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[ModelResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the model', metadata=[MaxLen(max_length=255)]), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[ModelResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str*

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* save_models_to_registry *: bool*

The save_models_to_registry property.

Returns:
: the value of the property.

#### *property* tags *: List[[TagResponse](zenml.models.md#zenml.models.TagResponse)]*

The tags property.

Returns:
: the value of the property.

#### *property* trade_offs *: str | None*

The trade_offs property.

Returns:
: the value of the property.

#### *property* use_cases *: str | None*

The use_cases property.

Returns:
: the value of the property.

#### *property* versions *: List[[Model](zenml.md#zenml.Model)]*

List all versions of the model.

Returns:
: The list of all model version.

### *class* zenml.models.v2.core.model.ModelResponseBody(\*, created: datetime, updated: datetime, user: [UserResponse](#zenml.models.v2.core.user.UserResponse) | None = None, tags: List[[TagResponse](#zenml.models.v2.core.tag.TagResponse)], latest_version_name: str | None = None, latest_version_id: UUID | None = None)

Bases: [`WorkspaceScopedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseBody)

Response body for models.

#### created *: datetime*

#### latest_version_id *: UUID | None*

#### latest_version_name *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'latest_version_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'latest_version_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'tags': FieldInfo(annotation=List[TagResponse], required=True, title='Tags associated with the model'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.'), 'user': FieldInfo(annotation=Union[UserResponse, NoneType], required=False, default=None, title='The user who created this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### tags *: List[[TagResponse](zenml.models.md#zenml.models.TagResponse)]*

#### updated *: datetime*

#### user *: 'UserResponse' | None*

### *class* zenml.models.v2.core.model.ModelResponseMetadata(\*, workspace: [WorkspaceResponse](#zenml.models.v2.core.workspace.WorkspaceResponse), license: Annotated[str | None, MaxLen(max_length=65535)] = None, description: Annotated[str | None, MaxLen(max_length=65535)] = None, audience: Annotated[str | None, MaxLen(max_length=65535)] = None, use_cases: Annotated[str | None, MaxLen(max_length=65535)] = None, limitations: Annotated[str | None, MaxLen(max_length=65535)] = None, trade_offs: Annotated[str | None, MaxLen(max_length=65535)] = None, ethics: Annotated[str | None, MaxLen(max_length=65535)] = None, save_models_to_registry: bool = True)

Bases: [`WorkspaceScopedResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseMetadata)

Response metadata for models.

#### audience *: str | None*

#### description *: str | None*

#### ethics *: str | None*

#### license *: str | None*

#### limitations *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'audience': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The target audience of the model', metadata=[MaxLen(max_length=65535)]), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The description of the model', metadata=[MaxLen(max_length=65535)]), 'ethics': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The ethical implications of the model', metadata=[MaxLen(max_length=65535)]), 'license': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The license model created under', metadata=[MaxLen(max_length=65535)]), 'limitations': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The know limitations of the model', metadata=[MaxLen(max_length=65535)]), 'save_models_to_registry': FieldInfo(annotation=bool, required=False, default=True, title='Whether to save all ModelArtifacts to Model Registry'), 'trade_offs': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The trade offs of the model', metadata=[MaxLen(max_length=65535)]), 'use_cases': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The use cases of the model', metadata=[MaxLen(max_length=65535)]), 'workspace': FieldInfo(annotation=WorkspaceResponse, required=True, title='The workspace of this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### save_models_to_registry *: bool*

#### trade_offs *: str | None*

#### use_cases *: str | None*

#### workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

### *class* zenml.models.v2.core.model.ModelResponseResources(\*\*extra_data: Any)

Bases: [`WorkspaceScopedResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseResources)

Class for all resource models associated with the model entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.model.ModelUpdate(\*, name: str | None = None, license: str | None = None, description: str | None = None, audience: str | None = None, use_cases: str | None = None, limitations: str | None = None, trade_offs: str | None = None, ethics: str | None = None, add_tags: List[str] | None = None, remove_tags: List[str] | None = None, save_models_to_registry: bool | None = None)

Bases: `BaseModel`

Update model for models.

#### add_tags *: List[str] | None*

#### audience *: str | None*

#### description *: str | None*

#### ethics *: str | None*

#### license *: str | None*

#### limitations *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'add_tags': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None), 'audience': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'ethics': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'license': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'limitations': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'remove_tags': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None), 'save_models_to_registry': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'trade_offs': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'use_cases': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

#### remove_tags *: List[str] | None*

#### save_models_to_registry *: bool | None*

#### trade_offs *: str | None*

#### use_cases *: str | None*

## zenml.models.v2.core.model_version module

Models representing model versions.

### *class* zenml.models.v2.core.model_version.ModelVersionFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None, tag: str | None = None, name: str | None = None, number: int | None = None, workspace_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, user_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, stage: Annotated[str | [ModelStages](zenml.md#zenml.enums.ModelStages) | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None)

Bases: [`WorkspaceScopedTaggableFilter`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedTaggableFilter)

Filter model for model versions.

#### apply_filter(query: AnyQuery, table: Type[AnySchema]) → AnyQuery

Applies the filter to a query.

Args:
: query: The query to which to apply the filter.
  table: The query table.

Returns:
: The query with filter applied.

#### created *: datetime | str | None*

#### id *: UUID | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The name of the Model Version'), 'number': FieldInfo(annotation=Union[int, NoneType], required=False, default=None, description='The number of the Model Version'), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'stage': FieldInfo(annotation=Union[str, ModelStages, NoneType], required=False, default=None, description='The model version stage', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'tag': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Tag to apply to the filter query.'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'user_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='The user of the Model Version', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'workspace_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='The workspace of the Model Version', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str | None*

#### number *: int | None*

#### page *: int*

#### scope_workspace *: UUID | None*

#### set_scope_model(model_name_or_id: str | UUID) → None

Set the model to scope this response.

Args:
: model_name_or_id: The model to scope this response to.

#### size *: int*

#### sort_by *: str*

#### stage *: str | [ModelStages](zenml.md#zenml.enums.ModelStages) | None*

#### tag *: str | None*

#### updated *: datetime | str | None*

#### user_id *: UUID | str | None*

#### workspace_id *: UUID | str | None*

### *class* zenml.models.v2.core.model_version.ModelVersionRequest(\*, user: UUID, workspace: UUID, name: Annotated[str | None, MaxLen(max_length=255)] = None, description: Annotated[str | None, MaxLen(max_length=65535)] = None, stage: Annotated[str | None, MaxLen(max_length=255)] = None, number: int | None = None, model: UUID, tags: List[str] | None = None)

Bases: [`WorkspaceScopedRequest`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedRequest)

Request model for model versions.

#### description *: str | None*

#### model *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The description of the model version', metadata=[MaxLen(max_length=65535)]), 'model': FieldInfo(annotation=UUID, required=True, description='The ID of the model containing version'), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The name of the model version', metadata=[MaxLen(max_length=255)]), 'number': FieldInfo(annotation=Union[int, NoneType], required=False, default=None, description='The number of the model version'), 'stage': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The stage of the model version', metadata=[MaxLen(max_length=255)]), 'tags': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None, title='Tags associated with the model version'), 'user': FieldInfo(annotation=UUID, required=True, title='The id of the user that created this resource.'), 'workspace': FieldInfo(annotation=UUID, required=True, title='The workspace to which this resource belongs.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

#### number *: int | None*

#### stage *: str | None*

#### tags *: List[str] | None*

#### user *: UUID*

#### workspace *: UUID*

### *class* zenml.models.v2.core.model_version.ModelVersionResponse(\*, body: [ModelVersionResponseBody](#zenml.models.v2.core.model_version.ModelVersionResponseBody) | None = None, metadata: [ModelVersionResponseMetadata](#zenml.models.v2.core.model_version.ModelVersionResponseMetadata) | None = None, resources: [ModelVersionResponseResources](#zenml.models.v2.core.model_version.ModelVersionResponseResources) | None = None, id: UUID, permission_denied: bool = False, name: Annotated[str | None, MaxLen(max_length=255)] = None)

Bases: `WorkspaceScopedResponse[ModelVersionResponseBody, ModelVersionResponseMetadata, ModelVersionResponseResources]`

Response model for model versions.

#### body *: 'AnyBody' | None*

#### *property* data_artifact_ids *: Dict[str, Dict[str, UUID]]*

The data_artifact_ids property.

Returns:
: the value of the property.

#### *property* data_artifacts *: Dict[str, Dict[str, [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse)]]*

Get all data artifacts linked to this model version.

Returns:
: Dictionary of data artifacts with versions as
  Dict[str, Dict[str, ArtifactResponse]]

#### *property* deployment_artifact_ids *: Dict[str, Dict[str, UUID]]*

The deployment_artifact_ids property.

Returns:
: the value of the property.

#### *property* deployment_artifacts *: Dict[str, Dict[str, [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse)]]*

Get all deployment artifacts linked to this model version.

Returns:
: Dictionary of deployment artifacts with versions as
  Dict[str, Dict[str, ArtifactResponse]]

#### *property* description *: str | None*

The description property.

Returns:
: the value of the property.

#### get_artifact(name: str, version: str | None = None) → [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse) | None

Get the artifact linked to this model version.

Args:
: name: The name of the artifact to retrieve.
  version: The version of the artifact to retrieve (None for
  <br/>
  > latest/non-versioned)

Returns:
: Specific version of an artifact or None

#### get_data_artifact(name: str, version: str | None = None) → [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse) | None

Get the data artifact linked to this model version.

Args:
: name: The name of the data artifact to retrieve.
  version: The version of the data artifact to retrieve (None for
  <br/>
  > latest/non-versioned)

Returns:
: Specific version of the data artifact or None

#### get_deployment_artifact(name: str, version: str | None = None) → [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse) | None

Get the deployment artifact linked to this model version.

Args:
: name: The name of the deployment artifact to retrieve.
  version: The version of the deployment artifact to retrieve (None for
  <br/>
  > latest/non-versioned)

Returns:
: Specific version of the deployment artifact or None

#### get_hydrated_version() → [ModelVersionResponse](#zenml.models.v2.core.model_version.ModelVersionResponse)

Get the hydrated version of this model version.

Returns:
: an instance of the same entity with the metadata field attached.

#### get_model_artifact(name: str, version: str | None = None) → [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse) | None

Get the model artifact linked to this model version.

Args:
: name: The name of the model artifact to retrieve.
  version: The version of the model artifact to retrieve (None for
  <br/>
  > latest/non-versioned)

Returns:
: Specific version of the model artifact or None

#### get_pipeline_run(name: str) → [PipelineRunResponse](zenml.models.md#zenml.models.PipelineRunResponse)

Get pipeline run linked to this version.

Args:
: name: The name of the pipeline run to retrieve.

Returns:
: PipelineRun as PipelineRunResponseModel

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### *property* model *: [ModelResponse](zenml.models.md#zenml.models.ModelResponse)*

The model property.

Returns:
: the value of the property.

#### *property* model_artifact_ids *: Dict[str, Dict[str, UUID]]*

The model_artifact_ids property.

Returns:
: the value of the property.

#### *property* model_artifacts *: Dict[str, Dict[str, [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse)]]*

Get all model artifacts linked to this model version.

Returns:
: Dictionary of model artifacts with versions as
  Dict[str, Dict[str, ArtifactResponse]]

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[ModelVersionResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[ModelVersionResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The name of the model version', metadata=[MaxLen(max_length=255)]), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[ModelVersionResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str | None*

#### *property* number *: int*

The number property.

Returns:
: the value of the property.

#### permission_denied *: bool*

#### *property* pipeline_run_ids *: Dict[str, UUID]*

The pipeline_run_ids property.

Returns:
: the value of the property.

#### *property* pipeline_runs *: Dict[str, [PipelineRunResponse](zenml.models.md#zenml.models.PipelineRunResponse)]*

Get all pipeline runs linked to this version.

Returns:
: Dictionary of Pipeline Runs as PipelineRunResponseModel

#### resources *: 'AnyResources' | None*

#### *property* run_metadata *: Dict[str, [RunMetadataResponse](zenml.models.md#zenml.models.RunMetadataResponse)] | None*

The run_metadata property.

Returns:
: the value of the property.

#### set_stage(stage: str | [ModelStages](zenml.md#zenml.enums.ModelStages), force: bool = False) → None

Sets this Model Version to a desired stage.

Args:
: stage: the target stage for model version.
  force: whether to force archiving of current model version in
  <br/>
  > target stage or raise.

Raises:
: ValueError: if model_stage is not valid.

#### *property* stage *: str | None*

The stage property.

Returns:
: the value of the property.

#### *property* tags *: List[[TagResponse](#zenml.models.v2.core.tag.TagResponse)]*

The tags property.

Returns:
: the value of the property.

#### to_model_class(was_created_in_this_run: bool = False, suppress_class_validation_warnings: bool = False) → [Model](zenml.md#zenml.Model)

Convert response model to Model object.

Args:
: was_created_in_this_run: Whether model version was created during
  : the current run.
  <br/>
  suppress_class_validation_warnings: internally used to suppress
  : repeated warnings.

Returns:
: Model object

### *class* zenml.models.v2.core.model_version.ModelVersionResponseBody(\*, created: datetime, updated: datetime, user: [UserResponse](#zenml.models.v2.core.user.UserResponse) | None = None, stage: Annotated[str | None, MaxLen(max_length=255)] = None, number: int, model: [ModelResponse](#zenml.models.v2.core.model.ModelResponse), model_artifact_ids: Dict[str, Dict[str, UUID]] = {}, data_artifact_ids: Dict[str, Dict[str, UUID]] = {}, deployment_artifact_ids: Dict[str, Dict[str, UUID]] = {}, pipeline_run_ids: Dict[str, UUID] = {}, tags: List[[TagResponse](#zenml.models.v2.core.tag.TagResponse)] = [])

Bases: [`WorkspaceScopedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseBody)

Response body for model versions.

#### created *: datetime*

#### data_artifact_ids *: Dict[str, Dict[str, UUID]]*

#### deployment_artifact_ids *: Dict[str, Dict[str, UUID]]*

#### model *: [ModelResponse](zenml.models.md#zenml.models.ModelResponse)*

#### model_artifact_ids *: Dict[str, Dict[str, UUID]]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'data_artifact_ids': FieldInfo(annotation=Dict[str, Dict[str, UUID]], required=False, default={}, description='Data artifacts linked to the model version'), 'deployment_artifact_ids': FieldInfo(annotation=Dict[str, Dict[str, UUID]], required=False, default={}, description='Deployment artifacts linked to the model version'), 'model': FieldInfo(annotation=ModelResponse, required=True, description='The model containing version'), 'model_artifact_ids': FieldInfo(annotation=Dict[str, Dict[str, UUID]], required=False, default={}, description='Model artifacts linked to the model version'), 'number': FieldInfo(annotation=int, required=True, description='The number of the model version'), 'pipeline_run_ids': FieldInfo(annotation=Dict[str, UUID], required=False, default={}, description='Pipeline runs linked to the model version'), 'stage': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The stage of the model version', metadata=[MaxLen(max_length=255)]), 'tags': FieldInfo(annotation=List[TagResponse], required=False, default=[], title='Tags associated with the model version'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.'), 'user': FieldInfo(annotation=Union[UserResponse, NoneType], required=False, default=None, title='The user who created this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### number *: int*

#### pipeline_run_ids *: Dict[str, UUID]*

#### stage *: str | None*

#### tags *: List[[TagResponse](#zenml.models.v2.core.tag.TagResponse)]*

#### updated *: datetime*

#### user *: 'UserResponse' | None*

### *class* zenml.models.v2.core.model_version.ModelVersionResponseMetadata(\*, workspace: [WorkspaceResponse](#zenml.models.v2.core.workspace.WorkspaceResponse), description: Annotated[str | None, MaxLen(max_length=65535)] = None, run_metadata: Dict[str, [RunMetadataResponse](#zenml.models.v2.core.run_metadata.RunMetadataResponse)] = {})

Bases: [`WorkspaceScopedResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseMetadata)

Response metadata for model versions.

#### description *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The description of the model version', metadata=[MaxLen(max_length=65535)]), 'run_metadata': FieldInfo(annotation=Dict[str, RunMetadataResponse], required=False, default={}, description='Metadata linked to the model version'), 'workspace': FieldInfo(annotation=WorkspaceResponse, required=True, title='The workspace of this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### run_metadata *: Dict[str, [RunMetadataResponse](zenml.models.md#zenml.models.RunMetadataResponse)]*

#### workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

### *class* zenml.models.v2.core.model_version.ModelVersionResponseResources(\*, services: [Page](zenml.models.v2.base.md#id327)[[ServiceResponse](zenml.models.md#zenml.models.ServiceResponse)], \*\*extra_data: Any)

Bases: [`WorkspaceScopedResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseResources)

Class for all resource models associated with the model version entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'services': FieldInfo(annotation=Page[ServiceResponse], required=True, description='Services linked to the model version')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### services *: [Page](zenml.models.v2.base.md#id327)[[ServiceResponse](zenml.models.md#zenml.models.ServiceResponse)]*

### *class* zenml.models.v2.core.model_version.ModelVersionUpdate(\*, model: UUID, stage: Annotated[str | [ModelStages](zenml.md#zenml.enums.ModelStages) | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, force: bool = False, name: str | None = None, description: str | None = None, add_tags: List[str] | None = None, remove_tags: List[str] | None = None)

Bases: `BaseModel`

Update model for model versions.

#### add_tags *: List[str] | None*

#### description *: str | None*

#### force *: bool*

#### model *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'add_tags': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None, description='Tags to be added to the model version'), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Target model version description to be set'), 'force': FieldInfo(annotation=bool, required=False, default=False, description='Whether existing model version in target stage should be silently archived or an error should be raised.'), 'model': FieldInfo(annotation=UUID, required=True, description='The ID of the model containing version'), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Target model version name to be set'), 'remove_tags': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None, description='Tags to be removed from the model version'), 'stage': FieldInfo(annotation=Union[str, ModelStages, NoneType], required=False, default=None, description='Target model version stage to be set', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

#### remove_tags *: List[str] | None*

#### stage *: str | [ModelStages](zenml.md#zenml.enums.ModelStages) | None*

## zenml.models.v2.core.model_version_artifact module

Models representing the link between model versions and artifacts.

### *class* zenml.models.v2.core.model_version_artifact.ModelVersionArtifactFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None, workspace_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, user_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, model_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, model_version_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, artifact_version_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, artifact_name: str | None = None, only_data_artifacts: bool | None = False, only_model_artifacts: bool | None = False, only_deployment_artifacts: bool | None = False, has_custom_name: bool | None = None)

Bases: [`WorkspaceScopedFilter`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedFilter)

Model version pipeline run links filter model.

#### CLI_EXCLUDE_FIELDS *: ClassVar[List[str]]* *= ['scope_workspace', 'only_data_artifacts', 'only_model_artifacts', 'only_deployment_artifacts', 'has_custom_name', 'model_id', 'model_version_id', 'user_id', 'workspace_id', 'updated', 'id']*

#### FILTER_EXCLUDE_FIELDS *: ClassVar[List[str]]* *= ['sort_by', 'page', 'size', 'logical_operator', 'scope_workspace', 'artifact_name', 'only_data_artifacts', 'only_model_artifacts', 'only_deployment_artifacts', 'has_custom_name']*

#### artifact_name *: str | None*

#### artifact_version_id *: UUID | str | None*

#### created *: datetime | str | None*

#### get_custom_filters() → List[ColumnElement[bool]]

Get custom filters.

Returns:
: A list of custom filters.

#### has_custom_name *: bool | None*

#### id *: UUID | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Name of the artifact'), 'artifact_version_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Filter by artifact ID', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'has_custom_name': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'model_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Filter by model ID', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'model_version_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Filter by model version ID', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'only_data_artifacts': FieldInfo(annotation=Union[bool, NoneType], required=False, default=False), 'only_deployment_artifacts': FieldInfo(annotation=Union[bool, NoneType], required=False, default=False), 'only_model_artifacts': FieldInfo(annotation=Union[bool, NoneType], required=False, default=False), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'user_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='The user of the Model Version', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'workspace_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='The workspace of the Model Version', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_id *: UUID | str | None*

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### model_version_id *: UUID | str | None*

#### only_data_artifacts *: bool | None*

#### only_deployment_artifacts *: bool | None*

#### only_model_artifacts *: bool | None*

#### page *: int*

#### scope_workspace *: UUID | None*

#### size *: int*

#### sort_by *: str*

#### updated *: datetime | str | None*

#### user_id *: UUID | str | None*

#### workspace_id *: UUID | str | None*

### *class* zenml.models.v2.core.model_version_artifact.ModelVersionArtifactRequest(\*, user: UUID, workspace: UUID, model: UUID, model_version: UUID, artifact_version: UUID, is_model_artifact: bool = False, is_deployment_artifact: bool = False)

Bases: [`WorkspaceScopedRequest`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedRequest)

Request model for links between model versions and artifacts.

#### artifact_version *: UUID*

#### is_deployment_artifact *: bool*

#### is_model_artifact *: bool*

#### model *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact_version': FieldInfo(annotation=UUID, required=True), 'is_deployment_artifact': FieldInfo(annotation=bool, required=False, default=False), 'is_model_artifact': FieldInfo(annotation=bool, required=False, default=False), 'model': FieldInfo(annotation=UUID, required=True), 'model_version': FieldInfo(annotation=UUID, required=True), 'user': FieldInfo(annotation=UUID, required=True, title='The id of the user that created this resource.'), 'workspace': FieldInfo(annotation=UUID, required=True, title='The workspace to which this resource belongs.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_version *: UUID*

#### user *: UUID*

#### workspace *: UUID*

### *class* zenml.models.v2.core.model_version_artifact.ModelVersionArtifactResponse(\*, body: [ModelVersionArtifactResponseBody](#zenml.models.v2.core.model_version_artifact.ModelVersionArtifactResponseBody) | None = None, metadata: [BaseResponseMetadata](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseMetadata) | None = None, resources: [ModelVersionArtifactResponseResources](#zenml.models.v2.core.model_version_artifact.ModelVersionArtifactResponseResources) | None = None, id: UUID, permission_denied: bool = False)

Bases: `BaseIdentifiedResponse[ModelVersionArtifactResponseBody, BaseResponseMetadata, ModelVersionArtifactResponseResources]`

Response model for links between model versions and artifacts.

#### *property* artifact_version *: [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse)*

The artifact_version property.

Returns:
: the value of the property.

#### body *: 'AnyBody' | None*

#### id *: UUID*

#### *property* is_deployment_artifact *: bool*

The is_deployment_artifact property.

Returns:
: the value of the property.

#### *property* is_model_artifact *: bool*

The is_model_artifact property.

Returns:
: the value of the property.

#### metadata *: 'AnyMetadata' | None*

#### *property* model *: UUID*

The model property.

Returns:
: the value of the property.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[ModelVersionArtifactResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[BaseResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[ModelVersionArtifactResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### *property* model_version *: UUID*

The model_version property.

Returns:
: the value of the property.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

### *class* zenml.models.v2.core.model_version_artifact.ModelVersionArtifactResponseBody(\*, created: datetime, updated: datetime, model: UUID, model_version: UUID, artifact_version: [ArtifactVersionResponse](#zenml.models.v2.core.artifact_version.ArtifactVersionResponse), is_model_artifact: bool = False, is_deployment_artifact: bool = False)

Bases: [`BaseDatedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseDatedResponseBody)

Response body for links between model versions and artifacts.

#### artifact_version *: [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse)*

#### created *: datetime*

#### is_deployment_artifact *: bool*

#### is_model_artifact *: bool*

#### model *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact_version': FieldInfo(annotation=ArtifactVersionResponse, required=True), 'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'is_deployment_artifact': FieldInfo(annotation=bool, required=False, default=False), 'is_model_artifact': FieldInfo(annotation=bool, required=False, default=False), 'model': FieldInfo(annotation=UUID, required=True), 'model_version': FieldInfo(annotation=UUID, required=True), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_version *: UUID*

#### updated *: datetime*

### *class* zenml.models.v2.core.model_version_artifact.ModelVersionArtifactResponseResources(\*\*extra_data: Any)

Bases: [`BaseResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseResources)

Class for all resource models associated with the model version artifact entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## zenml.models.v2.core.model_version_pipeline_run module

Models representing the link between model versions and pipeline runs.

### *class* zenml.models.v2.core.model_version_pipeline_run.ModelVersionPipelineRunFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None, workspace_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, user_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, model_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, model_version_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, pipeline_run_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, pipeline_run_name: str | None = None)

Bases: [`WorkspaceScopedFilter`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedFilter)

Model version pipeline run links filter model.

#### CLI_EXCLUDE_FIELDS *: ClassVar[List[str]]* *= ['scope_workspace', 'model_id', 'model_version_id', 'user_id', 'workspace_id', 'updated', 'id']*

#### FILTER_EXCLUDE_FIELDS *: ClassVar[List[str]]* *= ['sort_by', 'page', 'size', 'logical_operator', 'scope_workspace', 'pipeline_run_name']*

#### created *: datetime | str | None*

#### get_custom_filters() → List[ColumnElement[bool]]

Get custom filters.

Returns:
: A list of custom filters.

#### id *: UUID | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'model_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Filter by model ID', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'model_version_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Filter by model version ID', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'pipeline_run_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Filter by pipeline run ID', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'pipeline_run_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Name of the pipeline run'), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'user_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='The user of the Model Version', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'workspace_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='The workspace of the Model Version', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_id *: UUID | str | None*

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### model_version_id *: UUID | str | None*

#### page *: int*

#### pipeline_run_id *: UUID | str | None*

#### pipeline_run_name *: str | None*

#### scope_workspace *: UUID | None*

#### size *: int*

#### sort_by *: str*

#### updated *: datetime | str | None*

#### user_id *: UUID | str | None*

#### workspace_id *: UUID | str | None*

### *class* zenml.models.v2.core.model_version_pipeline_run.ModelVersionPipelineRunRequest(\*, user: UUID, workspace: UUID, model: UUID, model_version: UUID, pipeline_run: UUID)

Bases: [`WorkspaceScopedRequest`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedRequest)

Request model for links between model versions and pipeline runs.

#### model *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'model': FieldInfo(annotation=UUID, required=True), 'model_version': FieldInfo(annotation=UUID, required=True), 'pipeline_run': FieldInfo(annotation=UUID, required=True), 'user': FieldInfo(annotation=UUID, required=True, title='The id of the user that created this resource.'), 'workspace': FieldInfo(annotation=UUID, required=True, title='The workspace to which this resource belongs.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_version *: UUID*

#### pipeline_run *: UUID*

#### user *: UUID*

#### workspace *: UUID*

### *class* zenml.models.v2.core.model_version_pipeline_run.ModelVersionPipelineRunResponse(\*, body: [ModelVersionPipelineRunResponseBody](#zenml.models.v2.core.model_version_pipeline_run.ModelVersionPipelineRunResponseBody) | None = None, metadata: [BaseResponseMetadata](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseMetadata) | None = None, resources: [ModelVersionPipelineRunResponseResources](#zenml.models.v2.core.model_version_pipeline_run.ModelVersionPipelineRunResponseResources) | None = None, id: UUID, permission_denied: bool = False)

Bases: `BaseIdentifiedResponse[ModelVersionPipelineRunResponseBody, BaseResponseMetadata, ModelVersionPipelineRunResponseResources]`

Response model for links between model versions and pipeline runs.

#### body *: 'AnyBody' | None*

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### *property* model *: UUID*

The model property.

Returns:
: the value of the property.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[ModelVersionPipelineRunResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[BaseResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[ModelVersionPipelineRunResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### *property* model_version *: UUID*

The model_version property.

Returns:
: the value of the property.

#### permission_denied *: bool*

#### *property* pipeline_run *: [PipelineRunResponse](#zenml.models.v2.core.pipeline_run.PipelineRunResponse)*

The pipeline_run property.

Returns:
: the value of the property.

#### resources *: 'AnyResources' | None*

### *class* zenml.models.v2.core.model_version_pipeline_run.ModelVersionPipelineRunResponseBody(\*, created: datetime, updated: datetime, model: UUID, model_version: UUID, pipeline_run: [PipelineRunResponse](#zenml.models.v2.core.pipeline_run.PipelineRunResponse))

Bases: [`BaseDatedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseDatedResponseBody)

Response body for links between model versions and pipeline runs.

#### created *: datetime*

#### model *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'model': FieldInfo(annotation=UUID, required=True), 'model_version': FieldInfo(annotation=UUID, required=True), 'pipeline_run': FieldInfo(annotation=PipelineRunResponse, required=True), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_version *: UUID*

#### pipeline_run *: [PipelineRunResponse](#zenml.models.v2.core.pipeline_run.PipelineRunResponse)*

#### updated *: datetime*

### *class* zenml.models.v2.core.model_version_pipeline_run.ModelVersionPipelineRunResponseResources(\*\*extra_data: Any)

Bases: [`BaseResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseResources)

Class for all resource models associated with the model version pipeline run entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## zenml.models.v2.core.pipeline module

Models representing pipelines.

### *class* zenml.models.v2.core.pipeline.PipelineFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None, tag: str | None = None, name: str | None = None, workspace_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, user_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None)

Bases: [`WorkspaceScopedTaggableFilter`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedTaggableFilter)

Pipeline filter model.

#### CUSTOM_SORTING_OPTIONS *: ClassVar[List[str]]* *= ['latest_run']*

#### apply_sorting(query: AnyQuery, table: Type[AnySchema]) → AnyQuery

Apply sorting to the query.

Args:
: query: The query to which to apply the sorting.
  table: The query table.

Returns:
: The query with sorting applied.

#### created *: datetime | str | None*

#### id *: UUID | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Name of the Pipeline'), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'tag': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Tag to apply to the filter query.'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'user_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='User of the Pipeline', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'workspace_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Workspace of the Pipeline', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str | None*

#### page *: int*

#### scope_workspace *: UUID | None*

#### size *: int*

#### sort_by *: str*

#### tag *: str | None*

#### updated *: datetime | str | None*

#### user_id *: UUID | str | None*

#### workspace_id *: UUID | str | None*

### *class* zenml.models.v2.core.pipeline.PipelineRequest(\*, user: UUID, workspace: UUID, name: Annotated[str, MaxLen(max_length=255)], description: Annotated[str | None, MaxLen(max_length=65535)] = None, tags: List[str] | None = None)

Bases: [`WorkspaceScopedRequest`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedRequest)

Request model for pipelines.

#### description *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The description of the pipeline.', metadata=[MaxLen(max_length=65535)]), 'name': FieldInfo(annotation=str, required=True, title='The name of the pipeline.', metadata=[MaxLen(max_length=255)]), 'tags': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None, title='Tags of the pipeline.'), 'user': FieldInfo(annotation=UUID, required=True, title='The id of the user that created this resource.'), 'workspace': FieldInfo(annotation=UUID, required=True, title='The workspace to which this resource belongs.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### tags *: List[str] | None*

#### user *: UUID*

#### workspace *: UUID*

### *class* zenml.models.v2.core.pipeline.PipelineResponse(\*, body: [PipelineResponseBody](#zenml.models.v2.core.pipeline.PipelineResponseBody) | None = None, metadata: [PipelineResponseMetadata](#zenml.models.v2.core.pipeline.PipelineResponseMetadata) | None = None, resources: [PipelineResponseResources](#zenml.models.v2.core.pipeline.PipelineResponseResources) | None = None, id: UUID, permission_denied: bool = False, name: Annotated[str, MaxLen(max_length=255)])

Bases: `WorkspaceScopedResponse[PipelineResponseBody, PipelineResponseMetadata, PipelineResponseResources]`

Response model for pipelines.

#### body *: 'AnyBody' | None*

#### get_hydrated_version() → [PipelineResponse](#zenml.models.v2.core.pipeline.PipelineResponse)

Get the hydrated version of this pipeline.

Returns:
: an instance of the same entity with the metadata field attached.

#### get_runs(\*\*kwargs: Any) → List[[PipelineRunResponse](zenml.models.md#zenml.models.PipelineRunResponse)]

Get runs of this pipeline.

Can be used to fetch runs other than self.runs and supports
fine-grained filtering and pagination.

Args:
: ```
  **
  ```
  <br/>
  kwargs: Further arguments for filtering or pagination that are
  : passed to client.list_pipeline_runs().

Returns:
: List of runs of this pipeline.

#### id *: UUID*

#### *property* last_run *: [PipelineRunResponse](zenml.models.md#zenml.models.PipelineRunResponse)*

Returns the last run of this pipeline.

Returns:
: The last run of this pipeline.

Raises:
: RuntimeError: If no runs were found for this pipeline.

#### *property* last_successful_run *: [PipelineRunResponse](zenml.models.md#zenml.models.PipelineRunResponse)*

Returns the last successful run of this pipeline.

Returns:
: The last successful run of this pipeline.

Raises:
: RuntimeError: If no successful runs were found for this pipeline.

#### *property* latest_run_id *: UUID | None*

The latest_run_id property.

Returns:
: the value of the property.

#### *property* latest_run_status *: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus) | None*

The latest_run_status property.

Returns:
: the value of the property.

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[PipelineResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[PipelineResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the pipeline.', metadata=[MaxLen(max_length=255)]), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[PipelineResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str*

#### *property* num_runs *: int*

Returns the number of runs of this pipeline.

Returns:
: The number of runs of this pipeline.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* runs *: List[[PipelineRunResponse](zenml.models.md#zenml.models.PipelineRunResponse)]*

Returns the 20 most recent runs of this pipeline in descending order.

Returns:
: The 20 most recent runs of this pipeline in descending order.

#### *property* tags *: List[[TagResponse](#zenml.models.v2.core.tag.TagResponse)]*

The tags property.

Returns:
: the value of the property.

### *class* zenml.models.v2.core.pipeline.PipelineResponseBody(\*, created: datetime, updated: datetime, user: [UserResponse](#zenml.models.v2.core.user.UserResponse) | None = None, latest_run_id: UUID | None = None, latest_run_status: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus) | None = None)

Bases: [`WorkspaceScopedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseBody)

Response body for pipelines.

#### created *: datetime*

#### latest_run_id *: UUID | None*

#### latest_run_status *: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus) | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'latest_run_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The ID of the latest run of the pipeline.'), 'latest_run_status': FieldInfo(annotation=Union[ExecutionStatus, NoneType], required=False, default=None, title='The status of the latest run of the pipeline.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.'), 'user': FieldInfo(annotation=Union[UserResponse, NoneType], required=False, default=None, title='The user who created this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### updated *: datetime*

#### user *: 'UserResponse' | None*

### *class* zenml.models.v2.core.pipeline.PipelineResponseMetadata(\*, workspace: [WorkspaceResponse](#zenml.models.v2.core.workspace.WorkspaceResponse), description: str | None = None)

Bases: [`WorkspaceScopedResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseMetadata)

Response metadata for pipelines.

#### description *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The description of the pipeline.'), 'workspace': FieldInfo(annotation=WorkspaceResponse, required=True, title='The workspace of this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

### *class* zenml.models.v2.core.pipeline.PipelineResponseResources(\*, tags: List[[TagResponse](#zenml.models.v2.core.tag.TagResponse)], \*\*extra_data: Any)

Bases: [`WorkspaceScopedResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseResources)

Class for all resource models associated with the pipeline entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'tags': FieldInfo(annotation=List[TagResponse], required=True, title='Tags associated with the pipeline.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### tags *: List[[TagResponse](#zenml.models.v2.core.tag.TagResponse)]*

### *class* zenml.models.v2.core.pipeline.PipelineUpdate(\*, description: Annotated[str | None, MaxLen(max_length=65535)] = None, add_tags: List[str] | None = None, remove_tags: List[str] | None = None)

Bases: [`BaseUpdate`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseUpdate)

Update model for pipelines.

#### add_tags *: List[str] | None*

#### description *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'add_tags': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None, title='New tags to add to the pipeline.'), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The description of the pipeline.', metadata=[MaxLen(max_length=65535)]), 'remove_tags': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None, title='Tags to remove from the pipeline.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### remove_tags *: List[str] | None*

## zenml.models.v2.core.pipeline_build module

Models representing pipeline builds.

### *class* zenml.models.v2.core.pipeline_build.PipelineBuildBase(\*, images: Dict[str, [BuildItem](zenml.models.v2.misc.md#zenml.models.v2.misc.build_item.BuildItem)] = {}, is_local: bool, contains_code: bool, zenml_version: str | None = None, python_version: str | None = None)

Bases: [`BaseZenModel`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseZenModel)

Base model for pipeline builds.

#### contains_code *: bool*

#### get_image(component_key: str, step: str | None = None) → str

Get the image built for a specific key.

Args:
: component_key: The key for which to get the image.
  step: The pipeline step for which to get the image. If no image
  <br/>
  > exists for this step, will fall back to the pipeline image for
  > the same key.

Returns:
: The image name or digest.

#### *static* get_image_key(component_key: str, step: str | None = None) → str

Get the image key.

Args:
: component_key: The component key.
  step: The pipeline step for which the image was built.

Returns:
: The image key.

#### get_settings_checksum(component_key: str, step: str | None = None) → str | None

Get the settings checksum for a specific key.

Args:
: component_key: The key for which to get the checksum.
  step: The pipeline step for which to get the checksum. If no
  <br/>
  > image exists for this step, will fall back to the pipeline image
  > for the same key.

Returns:
: The settings checksum.

#### images *: Dict[str, [BuildItem](zenml.models.v2.misc.md#zenml.models.v2.misc.build_item.BuildItem)]*

#### is_local *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'contains_code': FieldInfo(annotation=bool, required=True, title='Whether any image of the build contains user code.'), 'images': FieldInfo(annotation=Dict[str, BuildItem], required=False, default={}, title='The images of this build.'), 'is_local': FieldInfo(annotation=bool, required=True, title='Whether the build images are stored in a container registry or locally.'), 'python_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The Python version used for this build.'), 'zenml_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The version of ZenML used for this build.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### python_version *: str | None*

#### *property* requires_code_download *: bool*

Whether the build requires code download.

Returns:
: Whether the build requires code download.

#### zenml_version *: str | None*

### *class* zenml.models.v2.core.pipeline_build.PipelineBuildFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None, workspace_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, user_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, pipeline_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, stack_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, is_local: bool | None = None, contains_code: bool | None = None, zenml_version: str | None = None, python_version: str | None = None, checksum: str | None = None)

Bases: [`WorkspaceScopedFilter`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedFilter)

Model to enable advanced filtering of all pipeline builds.

#### checksum *: str | None*

#### contains_code *: bool | None*

#### created *: datetime | str | None*

#### id *: UUID | str | None*

#### is_local *: bool | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'checksum': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The build checksum.'), 'contains_code': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, description='Whether any image of the build contains user code.'), 'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'is_local': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, description='Whether the build images are stored in a container registry or locally.'), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'pipeline_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Pipeline associated with the pipeline build.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'python_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The Python version used for this build.'), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'stack_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Stack used for the Pipeline Run', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'user_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='User that produced this pipeline build.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'workspace_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Workspace for this pipeline build.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'zenml_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The version of ZenML used for this build.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### page *: int*

#### pipeline_id *: UUID | str | None*

#### python_version *: str | None*

#### scope_workspace *: UUID | None*

#### size *: int*

#### sort_by *: str*

#### stack_id *: UUID | str | None*

#### updated *: datetime | str | None*

#### user_id *: UUID | str | None*

#### workspace_id *: UUID | str | None*

#### zenml_version *: str | None*

### *class* zenml.models.v2.core.pipeline_build.PipelineBuildRequest(\*, user: UUID, workspace: UUID, images: Dict[str, [BuildItem](zenml.models.v2.misc.md#zenml.models.v2.misc.build_item.BuildItem)] = {}, is_local: bool, contains_code: bool, zenml_version: str | None = None, python_version: str | None = None, checksum: str | None = None, stack_checksum: str | None = None, stack: UUID | None = None, pipeline: UUID | None = None)

Bases: [`PipelineBuildBase`](#zenml.models.v2.core.pipeline_build.PipelineBuildBase), [`WorkspaceScopedRequest`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedRequest)

Request model for pipelines builds.

#### checksum *: str | None*

#### contains_code *: bool*

#### images *: Dict[str, [BuildItem](zenml.models.md#zenml.models.BuildItem)]*

#### is_local *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'checksum': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The build checksum.'), 'contains_code': FieldInfo(annotation=bool, required=True, title='Whether any image of the build contains user code.'), 'images': FieldInfo(annotation=Dict[str, BuildItem], required=False, default={}, title='The images of this build.'), 'is_local': FieldInfo(annotation=bool, required=True, title='Whether the build images are stored in a container registry or locally.'), 'pipeline': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The pipeline that was used for this build.'), 'python_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The Python version used for this build.'), 'stack': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The stack that was used for this build.'), 'stack_checksum': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The stack checksum.'), 'user': FieldInfo(annotation=UUID, required=True, title='The id of the user that created this resource.'), 'workspace': FieldInfo(annotation=UUID, required=True, title='The workspace to which this resource belongs.'), 'zenml_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The version of ZenML used for this build.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### pipeline *: UUID | None*

#### python_version *: str | None*

#### stack *: UUID | None*

#### stack_checksum *: str | None*

#### user *: UUID*

#### workspace *: UUID*

#### zenml_version *: str | None*

### *class* zenml.models.v2.core.pipeline_build.PipelineBuildResponse(\*, body: [PipelineBuildResponseBody](#zenml.models.v2.core.pipeline_build.PipelineBuildResponseBody) | None = None, metadata: [PipelineBuildResponseMetadata](#zenml.models.v2.core.pipeline_build.PipelineBuildResponseMetadata) | None = None, resources: [PipelineBuildResponseResources](#zenml.models.v2.core.pipeline_build.PipelineBuildResponseResources) | None = None, id: UUID, permission_denied: bool = False)

Bases: `WorkspaceScopedResponse[PipelineBuildResponseBody, PipelineBuildResponseMetadata, PipelineBuildResponseResources]`

Response model for pipeline builds.

#### body *: 'AnyBody' | None*

#### *property* checksum *: str | None*

The checksum property.

Returns:
: the value of the property.

#### *property* contains_code *: bool*

The contains_code property.

Returns:
: the value of the property.

#### get_hydrated_version() → [PipelineBuildResponse](#zenml.models.v2.core.pipeline_build.PipelineBuildResponse)

Return the hydrated version of this pipeline build.

Returns:
: an instance of the same entity with the metadata field attached.

#### get_image(component_key: str, step: str | None = None) → str

Get the image built for a specific key.

Args:
: component_key: The key for which to get the image.
  step: The pipeline step for which to get the image. If no image
  <br/>
  > exists for this step, will fall back to the pipeline image for
  > the same key.

Returns:
: The image name or digest.

#### *static* get_image_key(component_key: str, step: str | None = None) → str

Get the image key.

Args:
: component_key: The component key.
  step: The pipeline step for which the image was built.

Returns:
: The image key.

#### get_settings_checksum(component_key: str, step: str | None = None) → str | None

Get the settings checksum for a specific key.

Args:
: component_key: The key for which to get the checksum.
  step: The pipeline step for which to get the checksum. If no
  <br/>
  > image exists for this step, will fall back to the pipeline image
  > for the same key.

Returns:
: The settings checksum.

#### id *: UUID*

#### *property* images *: Dict[str, [BuildItem](zenml.models.v2.misc.md#zenml.models.v2.misc.build_item.BuildItem)]*

The images property.

Returns:
: the value of the property.

#### *property* is_local *: bool*

The is_local property.

Returns:
: the value of the property.

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[PipelineBuildResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[PipelineBuildResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[PipelineBuildResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### *property* pipeline *: [PipelineResponse](zenml.models.md#zenml.models.PipelineResponse) | None*

The pipeline property.

Returns:
: the value of the property.

#### *property* python_version *: str | None*

The python_version property.

Returns:
: the value of the property.

#### *property* requires_code_download *: bool*

Whether the build requires code download.

Returns:
: Whether the build requires code download.

#### resources *: 'AnyResources' | None*

#### *property* stack *: [StackResponse](zenml.models.md#zenml.models.StackResponse) | None*

The stack property.

Returns:
: the value of the property.

#### *property* stack_checksum *: str | None*

The stack_checksum property.

Returns:
: the value of the property.

#### to_yaml() → Dict[str, Any]

Create a yaml representation of the pipeline build.

Create a yaml representation of the pipeline build that can be used
to create a PipelineBuildBase instance.

Returns:
: The yaml representation of the pipeline build.

#### *property* zenml_version *: str | None*

The zenml_version property.

Returns:
: the value of the property.

### *class* zenml.models.v2.core.pipeline_build.PipelineBuildResponseBody(\*, created: datetime, updated: datetime, user: [UserResponse](#zenml.models.v2.core.user.UserResponse) | None = None)

Bases: [`WorkspaceScopedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseBody)

Response body for pipeline builds.

#### created *: datetime*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.'), 'user': FieldInfo(annotation=Union[UserResponse, NoneType], required=False, default=None, title='The user who created this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### updated *: datetime*

#### user *: [UserResponse](zenml.models.md#zenml.models.UserResponse) | None*

### *class* zenml.models.v2.core.pipeline_build.PipelineBuildResponseMetadata(\*, workspace: [WorkspaceResponse](#zenml.models.v2.core.workspace.WorkspaceResponse), pipeline: [PipelineResponse](#zenml.models.v2.core.pipeline.PipelineResponse) | None = None, stack: [StackResponse](#zenml.models.v2.core.stack.StackResponse) | None = None, images: Dict[str, [BuildItem](zenml.models.v2.misc.md#zenml.models.v2.misc.build_item.BuildItem)] = {}, zenml_version: str | None = None, python_version: str | None = None, checksum: str | None = None, stack_checksum: str | None = None, is_local: bool, contains_code: bool)

Bases: [`WorkspaceScopedResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseMetadata)

Response metadata for pipeline builds.

#### checksum *: str | None*

#### contains_code *: bool*

#### images *: Dict[str, [BuildItem](zenml.models.md#zenml.models.BuildItem)]*

#### is_local *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'checksum': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The build checksum.'), 'contains_code': FieldInfo(annotation=bool, required=True, title='Whether any image of the build contains user code.'), 'images': FieldInfo(annotation=Dict[str, BuildItem], required=False, default={}, title='The images of this build.'), 'is_local': FieldInfo(annotation=bool, required=True, title='Whether the build images are stored in a container registry or locally.'), 'pipeline': FieldInfo(annotation=Union[PipelineResponse, NoneType], required=False, default=None, title='The pipeline that was used for this build.'), 'python_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The Python version used for this build.'), 'stack': FieldInfo(annotation=Union[StackResponse, NoneType], required=False, default=None, title='The stack that was used for this build.'), 'stack_checksum': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The stack checksum.'), 'workspace': FieldInfo(annotation=WorkspaceResponse, required=True, title='The workspace of this resource.'), 'zenml_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The version of ZenML used for this build.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### pipeline *: [PipelineResponse](zenml.models.md#zenml.models.PipelineResponse) | None*

#### python_version *: str | None*

#### stack *: [StackResponse](zenml.models.md#zenml.models.StackResponse) | None*

#### stack_checksum *: str | None*

#### workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

#### zenml_version *: str | None*

### *class* zenml.models.v2.core.pipeline_build.PipelineBuildResponseResources(\*\*extra_data: Any)

Bases: [`WorkspaceScopedResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseResources)

Class for all resource models associated with the pipeline build entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## zenml.models.v2.core.pipeline_deployment module

Models representing pipeline deployments.

### *class* zenml.models.v2.core.pipeline_deployment.PipelineDeploymentBase(\*, run_name_template: str, pipeline_configuration: [PipelineConfiguration](zenml.config.md#zenml.config.pipeline_configurations.PipelineConfiguration), step_configurations: Dict[str, [Step](zenml.config.md#zenml.config.step_configurations.Step)] = {}, client_environment: Dict[str, str] = {}, client_version: str | None = None, server_version: str | None = None, pipeline_version_hash: str | None = None, pipeline_spec: [PipelineSpec](zenml.config.md#zenml.config.pipeline_spec.PipelineSpec) | None = None)

Bases: [`BaseZenModel`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseZenModel)

Base model for pipeline deployments.

#### client_environment *: Dict[str, str]*

#### client_version *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'client_environment': FieldInfo(annotation=Dict[str, str], required=False, default={}, title='The client environment for this deployment.'), 'client_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The version of the ZenML installation on the client side.'), 'pipeline_configuration': FieldInfo(annotation=PipelineConfiguration, required=True, title='The pipeline configuration for this deployment.'), 'pipeline_spec': FieldInfo(annotation=Union[PipelineSpec, NoneType], required=False, default=None, title='The pipeline spec of the deployment.'), 'pipeline_version_hash': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The pipeline version hash of the deployment.'), 'run_name_template': FieldInfo(annotation=str, required=True, title='The run name template for runs created using this deployment.'), 'server_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The version of the ZenML installation on the server side.'), 'step_configurations': FieldInfo(annotation=Dict[str, Step], required=False, default={}, title='The step configurations for this deployment.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### pipeline_configuration *: [PipelineConfiguration](zenml.config.md#zenml.config.pipeline_configurations.PipelineConfiguration)*

#### pipeline_spec *: [PipelineSpec](zenml.config.md#zenml.config.pipeline_spec.PipelineSpec) | None*

#### pipeline_version_hash *: str | None*

#### run_name_template *: str*

#### server_version *: str | None*

#### *property* should_prevent_build_reuse *: bool*

Whether the deployment prevents a build reuse.

Returns:
: Whether the deployment prevents a build reuse.

#### step_configurations *: Dict[str, [Step](zenml.config.md#zenml.config.step_configurations.Step)]*

### *class* zenml.models.v2.core.pipeline_deployment.PipelineDeploymentFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None, workspace_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, user_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, pipeline_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, stack_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, build_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, schedule_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, template_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None)

Bases: [`WorkspaceScopedFilter`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedFilter)

Model to enable advanced filtering of all pipeline deployments.

#### build_id *: UUID | str | None*

#### created *: datetime | str | None*

#### id *: UUID | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'build_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Build associated with the deployment.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'pipeline_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Pipeline associated with the deployment.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'schedule_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Schedule associated with the deployment.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'stack_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Stack associated with the deployment.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'template_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Template used as base for the deployment.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'user_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='User that created this deployment.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'workspace_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Workspace for this deployment.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### page *: int*

#### pipeline_id *: UUID | str | None*

#### schedule_id *: UUID | str | None*

#### scope_workspace *: UUID | None*

#### size *: int*

#### sort_by *: str*

#### stack_id *: UUID | str | None*

#### template_id *: UUID | str | None*

#### updated *: datetime | str | None*

#### user_id *: UUID | str | None*

#### workspace_id *: UUID | str | None*

### *class* zenml.models.v2.core.pipeline_deployment.PipelineDeploymentRequest(\*, user: UUID, workspace: UUID, run_name_template: str, pipeline_configuration: [PipelineConfiguration](zenml.config.md#zenml.config.pipeline_configurations.PipelineConfiguration), step_configurations: Dict[str, [Step](zenml.config.md#zenml.config.step_configurations.Step)] = {}, client_environment: Dict[str, str] = {}, client_version: str | None = None, server_version: str | None = None, pipeline_version_hash: str | None = None, pipeline_spec: [PipelineSpec](zenml.config.md#zenml.config.pipeline_spec.PipelineSpec) | None = None, stack: UUID, pipeline: UUID | None = None, build: UUID | None = None, schedule: UUID | None = None, code_reference: [CodeReferenceRequest](#zenml.models.v2.core.code_reference.CodeReferenceRequest) | None = None, code_path: str | None = None, template: UUID | None = None)

Bases: [`PipelineDeploymentBase`](#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentBase), [`WorkspaceScopedRequest`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedRequest)

Request model for pipeline deployments.

#### build *: UUID | None*

#### client_environment *: Dict[str, str]*

#### client_version *: str | None*

#### code_path *: str | None*

#### code_reference *: [CodeReferenceRequest](zenml.models.md#zenml.models.CodeReferenceRequest) | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'build': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The build associated with the deployment.'), 'client_environment': FieldInfo(annotation=Dict[str, str], required=False, default={}, title='The client environment for this deployment.'), 'client_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The version of the ZenML installation on the client side.'), 'code_path': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Optional path where the code is stored in the artifact store.'), 'code_reference': FieldInfo(annotation=Union[CodeReferenceRequest, NoneType], required=False, default=None, title='The code reference associated with the deployment.'), 'pipeline': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The pipeline associated with the deployment.'), 'pipeline_configuration': FieldInfo(annotation=PipelineConfiguration, required=True, title='The pipeline configuration for this deployment.'), 'pipeline_spec': FieldInfo(annotation=Union[PipelineSpec, NoneType], required=False, default=None, title='The pipeline spec of the deployment.'), 'pipeline_version_hash': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The pipeline version hash of the deployment.'), 'run_name_template': FieldInfo(annotation=str, required=True, title='The run name template for runs created using this deployment.'), 'schedule': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The schedule associated with the deployment.'), 'server_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The version of the ZenML installation on the server side.'), 'stack': FieldInfo(annotation=UUID, required=True, title='The stack associated with the deployment.'), 'step_configurations': FieldInfo(annotation=Dict[str, Step], required=False, default={}, title='The step configurations for this deployment.'), 'template': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='Template used for the deployment.'), 'user': FieldInfo(annotation=UUID, required=True, title='The id of the user that created this resource.'), 'workspace': FieldInfo(annotation=UUID, required=True, title='The workspace to which this resource belongs.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### pipeline *: UUID | None*

#### pipeline_configuration *: [PipelineConfiguration](zenml.config.md#zenml.config.pipeline_configurations.PipelineConfiguration)*

#### pipeline_spec *: [PipelineSpec](zenml.config.md#zenml.config.pipeline_spec.PipelineSpec) | None*

#### pipeline_version_hash *: str | None*

#### run_name_template *: str*

#### schedule *: UUID | None*

#### server_version *: str | None*

#### stack *: UUID*

#### step_configurations *: Dict[str, [Step](zenml.config.md#zenml.config.step_configurations.Step)]*

#### template *: UUID | None*

#### user *: UUID*

#### workspace *: UUID*

### *class* zenml.models.v2.core.pipeline_deployment.PipelineDeploymentResponse(\*, body: [PipelineDeploymentResponseBody](#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentResponseBody) | None = None, metadata: [PipelineDeploymentResponseMetadata](#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentResponseMetadata) | None = None, resources: [PipelineDeploymentResponseResources](#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentResponseResources) | None = None, id: UUID, permission_denied: bool = False)

Bases: `WorkspaceScopedResponse[PipelineDeploymentResponseBody, PipelineDeploymentResponseMetadata, PipelineDeploymentResponseResources]`

Response model for pipeline deployments.

#### body *: 'AnyBody' | None*

#### *property* build *: [PipelineBuildResponse](#zenml.models.v2.core.pipeline_build.PipelineBuildResponse) | None*

The build property.

Returns:
: the value of the property.

#### *property* client_environment *: Dict[str, str]*

The client_environment property.

Returns:
: the value of the property.

#### *property* client_version *: str | None*

The client_version property.

Returns:
: the value of the property.

#### *property* code_path *: str | None*

The code_path property.

Returns:
: the value of the property.

#### *property* code_reference *: [CodeReferenceResponse](#zenml.models.v2.core.code_reference.CodeReferenceResponse) | None*

The code_reference property.

Returns:
: the value of the property.

#### get_hydrated_version() → [PipelineDeploymentResponse](#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentResponse)

Return the hydrated version of this pipeline deployment.

Returns:
: an instance of the same entity with the metadata field attached.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[PipelineDeploymentResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[PipelineDeploymentResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[PipelineDeploymentResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### *property* pipeline *: [PipelineResponse](#zenml.models.v2.core.pipeline.PipelineResponse) | None*

The pipeline property.

Returns:
: the value of the property.

#### *property* pipeline_configuration *: [PipelineConfiguration](zenml.config.md#zenml.config.pipeline_configurations.PipelineConfiguration)*

The pipeline_configuration property.

Returns:
: the value of the property.

#### *property* pipeline_spec *: [PipelineSpec](zenml.config.md#zenml.config.pipeline_spec.PipelineSpec) | None*

The pipeline_spec property.

Returns:
: the value of the property.

#### *property* pipeline_version_hash *: str | None*

The pipeline_version_hash property.

Returns:
: the value of the property.

#### resources *: 'AnyResources' | None*

#### *property* run_name_template *: str*

The run_name_template property.

Returns:
: the value of the property.

#### *property* schedule *: [ScheduleResponse](#zenml.models.v2.core.schedule.ScheduleResponse) | None*

The schedule property.

Returns:
: the value of the property.

#### *property* server_version *: str | None*

The server_version property.

Returns:
: the value of the property.

#### *property* stack *: [StackResponse](#zenml.models.v2.core.stack.StackResponse) | None*

The stack property.

Returns:
: the value of the property.

#### *property* step_configurations *: Dict[str, [Step](zenml.config.md#zenml.config.step_configurations.Step)]*

The step_configurations property.

Returns:
: the value of the property.

#### *property* template_id *: UUID | None*

The template_id property.

Returns:
: the value of the property.

### *class* zenml.models.v2.core.pipeline_deployment.PipelineDeploymentResponseBody(\*, created: datetime, updated: datetime, user: [UserResponse](#zenml.models.v2.core.user.UserResponse) | None = None)

Bases: [`WorkspaceScopedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseBody)

Response body for pipeline deployments.

#### created *: datetime*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.'), 'user': FieldInfo(annotation=Union[UserResponse, NoneType], required=False, default=None, title='The user who created this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### updated *: datetime*

#### user *: [UserResponse](zenml.models.md#zenml.models.UserResponse) | None*

### *class* zenml.models.v2.core.pipeline_deployment.PipelineDeploymentResponseMetadata(\*, workspace: [WorkspaceResponse](#zenml.models.v2.core.workspace.WorkspaceResponse), run_name_template: str, pipeline_configuration: [PipelineConfiguration](zenml.config.md#zenml.config.pipeline_configurations.PipelineConfiguration), step_configurations: Dict[str, [Step](zenml.config.md#zenml.config.step_configurations.Step)] = {}, client_environment: Dict[str, str] = {}, client_version: str | None, server_version: str | None, pipeline_version_hash: str | None = None, pipeline_spec: [PipelineSpec](zenml.config.md#zenml.config.pipeline_spec.PipelineSpec) | None = None, code_path: str | None = None, pipeline: [PipelineResponse](#zenml.models.v2.core.pipeline.PipelineResponse) | None = None, stack: [StackResponse](#zenml.models.v2.core.stack.StackResponse) | None = None, build: [PipelineBuildResponse](#zenml.models.v2.core.pipeline_build.PipelineBuildResponse) | None = None, schedule: [ScheduleResponse](#zenml.models.v2.core.schedule.ScheduleResponse) | None = None, code_reference: [CodeReferenceResponse](#zenml.models.v2.core.code_reference.CodeReferenceResponse) | None = None, template_id: UUID | None = None)

Bases: [`WorkspaceScopedResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseMetadata)

Response metadata for pipeline deployments.

#### build *: [PipelineBuildResponse](#zenml.models.v2.core.pipeline_build.PipelineBuildResponse) | None*

#### client_environment *: Dict[str, str]*

#### client_version *: str | None*

#### code_path *: str | None*

#### code_reference *: [CodeReferenceResponse](#zenml.models.v2.core.code_reference.CodeReferenceResponse) | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'build': FieldInfo(annotation=Union[PipelineBuildResponse, NoneType], required=False, default=None, title='The pipeline build associated with the deployment.'), 'client_environment': FieldInfo(annotation=Dict[str, str], required=False, default={}, title='The client environment for this deployment.'), 'client_version': FieldInfo(annotation=Union[str, NoneType], required=True, title='The version of the ZenML installation on the client side.'), 'code_path': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Optional path where the code is stored in the artifact store.'), 'code_reference': FieldInfo(annotation=Union[CodeReferenceResponse, NoneType], required=False, default=None, title='The code reference associated with the deployment.'), 'pipeline': FieldInfo(annotation=Union[PipelineResponse, NoneType], required=False, default=None, title='The pipeline associated with the deployment.'), 'pipeline_configuration': FieldInfo(annotation=PipelineConfiguration, required=True, title='The pipeline configuration for this deployment.'), 'pipeline_spec': FieldInfo(annotation=Union[PipelineSpec, NoneType], required=False, default=None, title='The pipeline spec of the deployment.'), 'pipeline_version_hash': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The pipeline version hash of the deployment.'), 'run_name_template': FieldInfo(annotation=str, required=True, title='The run name template for runs created using this deployment.'), 'schedule': FieldInfo(annotation=Union[ScheduleResponse, NoneType], required=False, default=None, title='The schedule associated with the deployment.'), 'server_version': FieldInfo(annotation=Union[str, NoneType], required=True, title='The version of the ZenML installation on the server side.'), 'stack': FieldInfo(annotation=Union[StackResponse, NoneType], required=False, default=None, title='The stack associated with the deployment.'), 'step_configurations': FieldInfo(annotation=Dict[str, Step], required=False, default={}, title='The step configurations for this deployment.'), 'template_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='Template used for the pipeline run.'), 'workspace': FieldInfo(annotation=WorkspaceResponse, required=True, title='The workspace of this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### pipeline *: [PipelineResponse](#zenml.models.v2.core.pipeline.PipelineResponse) | None*

#### pipeline_configuration *: [PipelineConfiguration](zenml.config.md#zenml.config.pipeline_configurations.PipelineConfiguration)*

#### pipeline_spec *: [PipelineSpec](zenml.config.md#zenml.config.pipeline_spec.PipelineSpec) | None*

#### pipeline_version_hash *: str | None*

#### run_name_template *: str*

#### schedule *: [ScheduleResponse](#zenml.models.v2.core.schedule.ScheduleResponse) | None*

#### server_version *: str | None*

#### stack *: [StackResponse](#zenml.models.v2.core.stack.StackResponse) | None*

#### step_configurations *: Dict[str, [Step](zenml.config.md#zenml.config.step_configurations.Step)]*

#### template_id *: UUID | None*

#### workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

### *class* zenml.models.v2.core.pipeline_deployment.PipelineDeploymentResponseResources(\*, triggers: TriggerPage, \*\*extra_data: Any)

Bases: [`WorkspaceScopedResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseResources)

Class for all resource models associated with the pipeline deployment entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'triggers': FieldInfo(annotation=~TriggerPage, required=True, title='The triggers configured with this event source.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### triggers *: TriggerPage*

## zenml.models.v2.core.pipeline_run module

Models representing pipeline runs.

### *class* zenml.models.v2.core.pipeline_run.PipelineRunFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None, tag: str | None = None, name: str | None = None, orchestrator_run_id: str | None = None, pipeline_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, pipeline_name: str | None = None, workspace_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, user_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, stack_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, schedule_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, build_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, deployment_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, code_repository_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, template_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, status: str | None = None, start_time: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, end_time: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, unlisted: bool | None = None)

Bases: [`WorkspaceScopedTaggableFilter`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedTaggableFilter)

Model to enable advanced filtering of all Workspaces.

#### FILTER_EXCLUDE_FIELDS *: ClassVar[List[str]]* *= ['sort_by', 'page', 'size', 'logical_operator', 'scope_workspace', 'unlisted', 'code_repository_id', 'build_id', 'schedule_id', 'stack_id', 'template_id', 'pipeline_name']*

#### build_id *: UUID | str | None*

#### code_repository_id *: UUID | str | None*

#### created *: datetime | str | None*

#### deployment_id *: UUID | str | None*

#### end_time *: datetime | str | None*

#### get_custom_filters() → List[ColumnElement[bool]]

Get custom filters.

Returns:
: A list of custom filters.

#### id *: UUID | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'build_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Build used for the Pipeline Run', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'code_repository_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Code repository used for the Pipeline Run', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'deployment_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Deployment used for the Pipeline Run', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'end_time': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='End time for this run', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Name of the Pipeline Run'), 'orchestrator_run_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Name of the Pipeline Run within the orchestrator'), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'pipeline_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Pipeline associated with the Pipeline Run', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'pipeline_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Name of the pipeline associated with the run'), 'schedule_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Schedule that triggered the Pipeline Run', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'stack_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Stack used for the Pipeline Run', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'start_time': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Start time for this run', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'status': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Name of the Pipeline Run'), 'tag': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Tag to apply to the filter query.'), 'template_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Template used for the pipeline run.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'unlisted': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'user_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='User that created the Pipeline Run', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'workspace_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Workspace of the Pipeline Run', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str | None*

#### orchestrator_run_id *: str | None*

#### page *: int*

#### pipeline_id *: UUID | str | None*

#### pipeline_name *: str | None*

#### schedule_id *: UUID | str | None*

#### scope_workspace *: UUID | None*

#### size *: int*

#### sort_by *: str*

#### stack_id *: UUID | str | None*

#### start_time *: datetime | str | None*

#### status *: str | None*

#### tag *: str | None*

#### template_id *: UUID | str | None*

#### unlisted *: bool | None*

#### updated *: datetime | str | None*

#### user_id *: UUID | str | None*

#### workspace_id *: UUID | str | None*

### *class* zenml.models.v2.core.pipeline_run.PipelineRunRequest(\*, user: UUID, workspace: UUID, name: Annotated[str, MaxLen(max_length=255)], deployment: UUID, pipeline: UUID | None = None, orchestrator_run_id: Annotated[str | None, MaxLen(max_length=255)] = None, start_time: datetime | None = None, end_time: datetime | None = None, status: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus), client_environment: Dict[str, str] = {}, orchestrator_environment: Dict[str, str] = {}, trigger_execution_id: UUID | None = None, tags: List[str] | None = None, model_version_id: UUID | None = None)

Bases: [`WorkspaceScopedRequest`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedRequest)

Request model for pipeline runs.

#### client_environment *: Dict[str, str]*

#### deployment *: UUID*

#### end_time *: datetime | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'client_environment': FieldInfo(annotation=Dict[str, str], required=False, default={}, title='Environment of the client that initiated this pipeline run (OS, Python version, etc.).'), 'deployment': FieldInfo(annotation=UUID, required=True, title='The deployment associated with the pipeline run.'), 'end_time': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None, title='The end time of the pipeline run.'), 'model_version_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The ID of the model version that was configured by this pipeline run explicitly.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the pipeline run.', metadata=[MaxLen(max_length=255)]), 'orchestrator_environment': FieldInfo(annotation=Dict[str, str], required=False, default={}, title='Environment of the orchestrator that executed this pipeline run (OS, Python version, etc.).'), 'orchestrator_run_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The orchestrator run ID.', metadata=[MaxLen(max_length=255)]), 'pipeline': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The pipeline associated with the pipeline run.'), 'start_time': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None, title='The start time of the pipeline run.'), 'status': FieldInfo(annotation=ExecutionStatus, required=True, title='The status of the pipeline run.'), 'tags': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None, title='Tags of the pipeline run.'), 'trigger_execution_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='ID of the trigger execution that triggered this run.'), 'user': FieldInfo(annotation=UUID, required=True, title='The id of the user that created this resource.'), 'workspace': FieldInfo(annotation=UUID, required=True, title='The workspace to which this resource belongs.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_version_id *: UUID | None*

#### name *: str*

#### orchestrator_environment *: Dict[str, str]*

#### orchestrator_run_id *: str | None*

#### pipeline *: UUID | None*

#### start_time *: datetime | None*

#### status *: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus)*

#### tags *: List[str] | None*

#### trigger_execution_id *: UUID | None*

#### user *: UUID*

#### workspace *: UUID*

### *class* zenml.models.v2.core.pipeline_run.PipelineRunResponse(\*, body: [PipelineRunResponseBody](#zenml.models.v2.core.pipeline_run.PipelineRunResponseBody) | None = None, metadata: [PipelineRunResponseMetadata](#zenml.models.v2.core.pipeline_run.PipelineRunResponseMetadata) | None = None, resources: [PipelineRunResponseResources](#zenml.models.v2.core.pipeline_run.PipelineRunResponseResources) | None = None, id: UUID, permission_denied: bool = False, name: Annotated[str, MaxLen(max_length=255)])

Bases: `WorkspaceScopedResponse[PipelineRunResponseBody, PipelineRunResponseMetadata, PipelineRunResponseResources]`

Response model for pipeline runs.

#### *property* artifact_versions *: List[[ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse)]*

Get all artifact versions that are outputs of steps of this run.

Returns:
: All output artifact versions of this run (including cached ones).

#### body *: 'AnyBody' | None*

#### *property* build *: [PipelineBuildResponse](zenml.models.md#zenml.models.PipelineBuildResponse) | None*

The build property.

Returns:
: the value of the property.

#### *property* client_environment *: Dict[str, str]*

The client_environment property.

Returns:
: the value of the property.

#### *property* code_path *: str | None*

The code_path property.

Returns:
: the value of the property.

#### *property* code_reference *: [CodeReferenceResponse](zenml.models.md#zenml.models.CodeReferenceResponse) | None*

The schedule property.

Returns:
: the value of the property.

#### *property* config *: [PipelineConfiguration](zenml.config.md#zenml.config.pipeline_configurations.PipelineConfiguration)*

The config property.

Returns:
: the value of the property.

#### *property* deployment_id *: UUID | None*

The deployment_id property.

Returns:
: the value of the property.

#### *property* end_time *: datetime | None*

The end_time property.

Returns:
: the value of the property.

#### get_hydrated_version() → [PipelineRunResponse](#zenml.models.v2.core.pipeline_run.PipelineRunResponse)

Get the hydrated version of this pipeline run.

Returns:
: an instance of the same entity with the metadata field attached.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[PipelineRunResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[PipelineRunResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the pipeline run.', metadata=[MaxLen(max_length=255)]), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[PipelineRunResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### *property* model_version *: [ModelVersionResponse](#zenml.models.v2.core.model_version.ModelVersionResponse) | None*

The model_version property.

Returns:
: the value of the property.

#### *property* model_version_id *: UUID | None*

The model_version_id property.

Returns:
: the value of the property.

#### name *: str*

#### *property* orchestrator_environment *: Dict[str, str]*

The orchestrator_environment property.

Returns:
: the value of the property.

#### *property* orchestrator_run_id *: str | None*

The orchestrator_run_id property.

Returns:
: the value of the property.

#### permission_denied *: bool*

#### *property* pipeline *: [PipelineResponse](zenml.models.md#zenml.models.PipelineResponse) | None*

The pipeline property.

Returns:
: the value of the property.

#### *property* produced_artifact_versions *: List[[ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse)]*

Get all artifact versions produced during this pipeline run.

Returns:
: A list of all artifact versions produced during this pipeline run.

#### resources *: 'AnyResources' | None*

#### *property* run_metadata *: Dict[str, [RunMetadataResponse](zenml.models.md#zenml.models.RunMetadataResponse)]*

The run_metadata property.

Returns:
: the value of the property.

#### *property* schedule *: [ScheduleResponse](zenml.models.md#zenml.models.ScheduleResponse) | None*

The schedule property.

Returns:
: the value of the property.

#### *property* stack *: [StackResponse](zenml.models.md#zenml.models.StackResponse) | None*

The stack property.

Returns:
: the value of the property.

#### *property* start_time *: datetime | None*

The start_time property.

Returns:
: the value of the property.

#### *property* status *: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus)*

The status property.

Returns:
: the value of the property.

#### *property* steps *: Dict[str, [StepRunResponse](zenml.models.md#zenml.models.StepRunResponse)]*

The steps property.

Returns:
: the value of the property.

#### *property* tags *: List[[TagResponse](#zenml.models.v2.core.tag.TagResponse)]*

The tags property.

Returns:
: the value of the property.

#### *property* template_id *: UUID | None*

The template_id property.

Returns:
: the value of the property.

#### *property* trigger_execution *: [TriggerExecutionResponse](zenml.models.md#zenml.models.TriggerExecutionResponse) | None*

The trigger_execution property.

Returns:
: the value of the property.

### *class* zenml.models.v2.core.pipeline_run.PipelineRunResponseBody(\*, created: datetime, updated: datetime, user: [UserResponse](#zenml.models.v2.core.user.UserResponse) | None = None, status: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus), stack: [StackResponse](#zenml.models.v2.core.stack.StackResponse) | None = None, pipeline: [PipelineResponse](#zenml.models.v2.core.pipeline.PipelineResponse) | None = None, build: [PipelineBuildResponse](#zenml.models.v2.core.pipeline_build.PipelineBuildResponse) | None = None, schedule: [ScheduleResponse](#zenml.models.v2.core.schedule.ScheduleResponse) | None = None, code_reference: [CodeReferenceResponse](#zenml.models.v2.core.code_reference.CodeReferenceResponse) | None = None, deployment_id: UUID | None = None, trigger_execution: [TriggerExecutionResponse](#zenml.models.v2.core.trigger_execution.TriggerExecutionResponse) | None = None, model_version_id: UUID | None = None)

Bases: [`WorkspaceScopedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseBody)

Response body for pipeline runs.

#### build *: [PipelineBuildResponse](zenml.models.md#zenml.models.PipelineBuildResponse) | None*

#### code_reference *: [CodeReferenceResponse](zenml.models.md#zenml.models.CodeReferenceResponse) | None*

#### created *: datetime*

#### deployment_id *: UUID | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'build': FieldInfo(annotation=Union[PipelineBuildResponse, NoneType], required=False, default=None, title='The pipeline build that was used for this run.'), 'code_reference': FieldInfo(annotation=Union[CodeReferenceResponse, NoneType], required=False, default=None, title='The code reference that was used for this run.'), 'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'deployment_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The deployment that was used for this run.'), 'model_version_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The ID of the model version that was configured by this pipeline run explicitly.'), 'pipeline': FieldInfo(annotation=Union[PipelineResponse, NoneType], required=False, default=None, title='The pipeline this run belongs to.'), 'schedule': FieldInfo(annotation=Union[ScheduleResponse, NoneType], required=False, default=None, title='The schedule that was used for this run.'), 'stack': FieldInfo(annotation=Union[StackResponse, NoneType], required=False, default=None, title='The stack that was used for this run.'), 'status': FieldInfo(annotation=ExecutionStatus, required=True, title='The status of the pipeline run.'), 'trigger_execution': FieldInfo(annotation=Union[TriggerExecutionResponse, NoneType], required=False, default=None, title='The trigger execution that triggered this run.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.'), 'user': FieldInfo(annotation=Union[UserResponse, NoneType], required=False, default=None, title='The user who created this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_version_id *: UUID | None*

#### pipeline *: [PipelineResponse](zenml.models.md#zenml.models.PipelineResponse) | None*

#### schedule *: [ScheduleResponse](zenml.models.md#zenml.models.ScheduleResponse) | None*

#### stack *: [StackResponse](zenml.models.md#zenml.models.StackResponse) | None*

#### status *: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus)*

#### trigger_execution *: [TriggerExecutionResponse](zenml.models.md#zenml.models.TriggerExecutionResponse) | None*

#### updated *: datetime*

#### user *: 'UserResponse' | None*

### *class* zenml.models.v2.core.pipeline_run.PipelineRunResponseMetadata(\*, workspace: [WorkspaceResponse](#zenml.models.v2.core.workspace.WorkspaceResponse), run_metadata: Dict[str, [RunMetadataResponse](#zenml.models.v2.core.run_metadata.RunMetadataResponse)] = {}, steps: Dict[str, [StepRunResponse](#zenml.models.v2.core.step_run.StepRunResponse)] = {}, config: [PipelineConfiguration](zenml.config.md#zenml.config.pipeline_configurations.PipelineConfiguration), start_time: datetime | None = None, end_time: datetime | None = None, client_environment: Dict[str, str] = {}, orchestrator_environment: Dict[str, str] = {}, orchestrator_run_id: Annotated[str | None, MaxLen(max_length=255)] = None, code_path: str | None = None, template_id: UUID | None = None)

Bases: [`WorkspaceScopedResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseMetadata)

Response metadata for pipeline runs.

#### client_environment *: Dict[str, str]*

#### code_path *: str | None*

#### config *: [PipelineConfiguration](zenml.config.md#zenml.config.pipeline_configurations.PipelineConfiguration)*

#### end_time *: datetime | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'client_environment': FieldInfo(annotation=Dict[str, str], required=False, default={}, title='Environment of the client that initiated this pipeline run (OS, Python version, etc.).'), 'code_path': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Optional path where the code is stored in the artifact store.'), 'config': FieldInfo(annotation=PipelineConfiguration, required=True, title='The pipeline configuration used for this pipeline run.'), 'end_time': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None, title='The end time of the pipeline run.'), 'orchestrator_environment': FieldInfo(annotation=Dict[str, str], required=False, default={}, title='Environment of the orchestrator that executed this pipeline run (OS, Python version, etc.).'), 'orchestrator_run_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The orchestrator run ID.', metadata=[MaxLen(max_length=255)]), 'run_metadata': FieldInfo(annotation=Dict[str, RunMetadataResponse], required=False, default={}, title='Metadata associated with this pipeline run.'), 'start_time': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None, title='The start time of the pipeline run.'), 'steps': FieldInfo(annotation=Dict[str, StepRunResponse], required=False, default={}, title='The steps of this run.'), 'template_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='Template used for the pipeline run.'), 'workspace': FieldInfo(annotation=WorkspaceResponse, required=True, title='The workspace of this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### orchestrator_environment *: Dict[str, str]*

#### orchestrator_run_id *: str | None*

#### run_metadata *: Dict[str, [RunMetadataResponse](zenml.models.md#zenml.models.RunMetadataResponse)]*

#### start_time *: datetime | None*

#### steps *: Dict[str, [StepRunResponse](zenml.models.md#zenml.models.StepRunResponse)]*

#### template_id *: UUID | None*

#### workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

### *class* zenml.models.v2.core.pipeline_run.PipelineRunResponseResources(\*, model_version: [ModelVersionResponse](#zenml.models.v2.core.model_version.ModelVersionResponse) | None = None, tags: List[[TagResponse](#zenml.models.v2.core.tag.TagResponse)], \*\*extra_data: Any)

Bases: [`WorkspaceScopedResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseResources)

Class for all resource models associated with the pipeline run entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow', 'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'model_version': FieldInfo(annotation=Union[ModelVersionResponse, NoneType], required=False, default=None), 'tags': FieldInfo(annotation=List[TagResponse], required=True, title='Tags associated with the pipeline run.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_version *: [ModelVersionResponse](#zenml.models.v2.core.model_version.ModelVersionResponse) | None*

#### tags *: List[[TagResponse](#zenml.models.v2.core.tag.TagResponse)]*

### *class* zenml.models.v2.core.pipeline_run.PipelineRunUpdate(\*, status: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus) | None = None, end_time: datetime | None = None, model_version_id: UUID | None = None, add_tags: List[str] | None = None, remove_tags: List[str] | None = None)

Bases: `BaseModel`

Pipeline run update model.

#### add_tags *: List[str] | None*

#### end_time *: datetime | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'add_tags': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None, title='New tags to add to the pipeline run.'), 'end_time': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'model_version_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The ID of the model version that was configured by this pipeline run explicitly.'), 'remove_tags': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None, title='Tags to remove from the pipeline run.'), 'status': FieldInfo(annotation=Union[ExecutionStatus, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_version_id *: UUID | None*

#### remove_tags *: List[str] | None*

#### status *: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus) | None*

## zenml.models.v2.core.run_metadata module

Models representing run metadata.

### *class* zenml.models.v2.core.run_metadata.LazyRunMetadataResponse(\*, body: [RunMetadataResponseBody](#zenml.models.v2.core.run_metadata.RunMetadataResponseBody) | None = None, metadata: [RunMetadataResponseMetadata](#zenml.models.v2.core.run_metadata.RunMetadataResponseMetadata) | None = None, resources: [RunMetadataResponseResources](#zenml.models.v2.core.run_metadata.RunMetadataResponseResources) | None = None, id: UUID | None = None, permission_denied: bool = False, lazy_load_artifact_name: str | None = None, lazy_load_artifact_version: str | None = None, lazy_load_metadata_name: str | None = None, lazy_load_model: [Model](zenml.model.md#zenml.model.model.Model))

Bases: [`RunMetadataResponse`](#zenml.models.v2.core.run_metadata.RunMetadataResponse)

Lazy run metadata response.

Used if the run metadata is accessed from the model in
a pipeline context available only during pipeline compilation.

#### get_body() → None

Protects from misuse of the lazy loader.

Raises:
: RuntimeError: always

#### get_metadata() → None

Protects from misuse of the lazy loader.

Raises:
: RuntimeError: always

#### id *: UUID | None*

#### lazy_load_artifact_name *: str | None*

#### lazy_load_artifact_version *: str | None*

#### lazy_load_metadata_name *: str | None*

#### lazy_load_model *: [Model](zenml.model.md#zenml.model.model.Model)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[RunMetadataResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'lazy_load_artifact_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'lazy_load_artifact_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'lazy_load_metadata_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'lazy_load_model': FieldInfo(annotation=Model, required=True), 'metadata': FieldInfo(annotation=Union[RunMetadataResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[RunMetadataResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

### *class* zenml.models.v2.core.run_metadata.RunMetadataFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None, resource_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, resource_type: [MetadataResourceTypes](zenml.md#zenml.enums.MetadataResourceTypes) | None = None, stack_component_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, key: str | None = None, type: Annotated[str | [MetadataTypeEnum](zenml.metadata.md#zenml.metadata.metadata_types.MetadataTypeEnum) | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None)

Bases: [`WorkspaceScopedFilter`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedFilter)

Model to enable advanced filtering of run metadata.

#### created *: datetime | str | None*

#### id *: UUID | str | None*

#### key *: str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'key': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'resource_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'resource_type': FieldInfo(annotation=Union[MetadataResourceTypes, NoneType], required=False, default=None), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'stack_component_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'type': FieldInfo(annotation=Union[str, MetadataTypeEnum, NoneType], required=False, default=None, metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### page *: int*

#### resource_id *: UUID | str | None*

#### resource_type *: [MetadataResourceTypes](zenml.md#zenml.enums.MetadataResourceTypes) | None*

#### scope_workspace *: UUID | None*

#### size *: int*

#### sort_by *: str*

#### stack_component_id *: UUID | str | None*

#### type *: str | [MetadataTypeEnum](zenml.metadata.md#zenml.metadata.metadata_types.MetadataTypeEnum) | None*

#### updated *: datetime | str | None*

### *class* zenml.models.v2.core.run_metadata.RunMetadataRequest(\*, user: UUID, workspace: UUID, resource_id: UUID, resource_type: [MetadataResourceTypes](zenml.md#zenml.enums.MetadataResourceTypes), stack_component_id: UUID | None, values: Dict[str, str | int | float | bool | Dict[Any, Any] | List[Any] | Set[Any] | Tuple[Any, ...] | [Uri](zenml.metadata.md#zenml.metadata.metadata_types.Uri) | [Path](zenml.metadata.md#zenml.metadata.metadata_types.Path) | [DType](zenml.metadata.md#zenml.metadata.metadata_types.DType) | [StorageSize](zenml.metadata.md#zenml.metadata.metadata_types.StorageSize)], types: Dict[str, [MetadataTypeEnum](zenml.metadata.md#zenml.metadata.metadata_types.MetadataTypeEnum)])

Bases: [`WorkspaceScopedRequest`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedRequest)

Request model for run metadata.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'resource_id': FieldInfo(annotation=UUID, required=True, title='The ID of the resource that this metadata belongs to.'), 'resource_type': FieldInfo(annotation=MetadataResourceTypes, required=True, title='The type of the resource that this metadata belongs to.'), 'stack_component_id': FieldInfo(annotation=Union[UUID, NoneType], required=True, title='The ID of the stack component that this metadata belongs to.'), 'types': FieldInfo(annotation=Dict[str, MetadataTypeEnum], required=True, title='The types of the metadata to be created.'), 'user': FieldInfo(annotation=UUID, required=True, title='The id of the user that created this resource.'), 'values': FieldInfo(annotation=Dict[str, Union[str, int, float, bool, Dict[Any, Any], List[Any], Set[Any], Tuple[Any, ...], Uri, Path, DType, StorageSize]], required=True, title='The metadata to be created.'), 'workspace': FieldInfo(annotation=UUID, required=True, title='The workspace to which this resource belongs.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### resource_id *: UUID*

#### resource_type *: [MetadataResourceTypes](zenml.md#zenml.enums.MetadataResourceTypes)*

#### stack_component_id *: UUID | None*

#### types *: Dict[str, [MetadataTypeEnum](zenml.metadata.md#zenml.metadata.metadata_types.MetadataTypeEnum)]*

#### user *: UUID*

#### values *: Dict[str, MetadataType]*

#### workspace *: UUID*

### *class* zenml.models.v2.core.run_metadata.RunMetadataResponse(\*, body: [RunMetadataResponseBody](#zenml.models.v2.core.run_metadata.RunMetadataResponseBody) | None = None, metadata: [RunMetadataResponseMetadata](#zenml.models.v2.core.run_metadata.RunMetadataResponseMetadata) | None = None, resources: [RunMetadataResponseResources](#zenml.models.v2.core.run_metadata.RunMetadataResponseResources) | None = None, id: UUID, permission_denied: bool = False)

Bases: `WorkspaceScopedResponse[RunMetadataResponseBody, RunMetadataResponseMetadata, RunMetadataResponseResources]`

Response model for run metadata.

#### body *: 'AnyBody' | None*

#### get_hydrated_version() → [RunMetadataResponse](#zenml.models.v2.core.run_metadata.RunMetadataResponse)

Get the hydrated version of this run metadata.

Returns:
: an instance of the same entity with the metadata field attached.

#### id *: UUID*

#### *property* key *: str*

The key property.

Returns:
: the value of the property.

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[RunMetadataResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[RunMetadataResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[RunMetadataResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### *property* resource_id *: UUID*

The resource_id property.

Returns:
: the value of the property.

#### *property* resource_type *: [MetadataResourceTypes](zenml.md#zenml.enums.MetadataResourceTypes)*

The resource_type property.

Returns:
: the value of the property.

#### resources *: 'AnyResources' | None*

#### *property* stack_component_id *: UUID | None*

The stack_component_id property.

Returns:
: the value of the property.

#### *property* type *: [MetadataTypeEnum](zenml.metadata.md#zenml.metadata.metadata_types.MetadataTypeEnum)*

The type property.

Returns:
: the value of the property.

#### *property* value *: str | int | float | bool | Dict[Any, Any] | List[Any] | Set[Any] | Tuple[Any, ...] | [Uri](zenml.metadata.md#zenml.metadata.metadata_types.Uri) | [Path](zenml.metadata.md#zenml.metadata.metadata_types.Path) | [DType](zenml.metadata.md#zenml.metadata.metadata_types.DType) | [StorageSize](zenml.metadata.md#zenml.metadata.metadata_types.StorageSize)*

The value property.

Returns:
: the value of the property.

### *class* zenml.models.v2.core.run_metadata.RunMetadataResponseBody(\*, created: datetime, updated: datetime, user: [UserResponse](#zenml.models.v2.core.user.UserResponse) | None = None, key: str, value: Annotated[str | int | float | bool | Dict[Any, Any] | List[Any] | Set[Any] | Tuple[Any, ...] | [Uri](zenml.metadata.md#zenml.metadata.metadata_types.Uri) | [Path](zenml.metadata.md#zenml.metadata.metadata_types.Path) | [DType](zenml.metadata.md#zenml.metadata.metadata_types.DType) | [StorageSize](zenml.metadata.md#zenml.metadata.metadata_types.StorageSize), \_PydanticGeneralMetadata(union_mode='smart')], type: [MetadataTypeEnum](zenml.metadata.md#zenml.metadata.metadata_types.MetadataTypeEnum))

Bases: [`WorkspaceScopedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseBody)

Response body for run metadata.

#### created *: datetime*

#### key *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'key': FieldInfo(annotation=str, required=True, title='The key of the metadata.'), 'type': FieldInfo(annotation=MetadataTypeEnum, required=True, title='The type of the metadata.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.'), 'user': FieldInfo(annotation=Union[UserResponse, NoneType], required=False, default=None, title='The user who created this resource.'), 'value': FieldInfo(annotation=Union[str, int, float, bool, Dict[Any, Any], List[Any], Set[Any], Tuple[Any, ...], Uri, Path, DType, StorageSize], required=True, title='The value of the metadata.', metadata=[_PydanticGeneralMetadata(union_mode='smart')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### *classmethod* str_field_max_length_check(value: Any) → Any

Checks if the length of the value exceeds the maximum str length.

Args:
: value: the value set in the field

Returns:
: the value itself.

Raises:
: AssertionError: if the length of the field is longer than the
  : maximum threshold.

#### *classmethod* text_field_max_length_check(value: Any) → Any

Checks if the length of the value exceeds the maximum text length.

Args:
: value: the value set in the field

Returns:
: the value itself.

Raises:
: AssertionError: if the length of the field is longer than the
  : maximum threshold.

#### type *: [MetadataTypeEnum](zenml.metadata.md#zenml.metadata.metadata_types.MetadataTypeEnum)*

#### updated *: datetime*

#### user *: 'UserResponse' | None*

#### value *: str | int | float | bool | Dict[Any, Any] | List[Any] | Set[Any] | Tuple[Any, ...] | [Uri](zenml.metadata.md#zenml.metadata.metadata_types.Uri) | [Path](zenml.metadata.md#zenml.metadata.metadata_types.Path) | [DType](zenml.metadata.md#zenml.metadata.metadata_types.DType) | [StorageSize](zenml.metadata.md#zenml.metadata.metadata_types.StorageSize)*

### *class* zenml.models.v2.core.run_metadata.RunMetadataResponseMetadata(\*, workspace: [WorkspaceResponse](#zenml.models.v2.core.workspace.WorkspaceResponse), resource_id: UUID, resource_type: [MetadataResourceTypes](zenml.md#zenml.enums.MetadataResourceTypes), stack_component_id: UUID | None)

Bases: [`WorkspaceScopedResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseMetadata)

Response metadata for run metadata.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'resource_id': FieldInfo(annotation=UUID, required=True, title='The ID of the resource that this metadata belongs to.'), 'resource_type': FieldInfo(annotation=MetadataResourceTypes, required=True, title='The type of the resource that this metadata belongs to.'), 'stack_component_id': FieldInfo(annotation=Union[UUID, NoneType], required=True, title='The ID of the stack component that this metadata belongs to.'), 'workspace': FieldInfo(annotation=WorkspaceResponse, required=True, title='The workspace of this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### resource_id *: UUID*

#### resource_type *: [MetadataResourceTypes](zenml.md#zenml.enums.MetadataResourceTypes)*

#### stack_component_id *: UUID | None*

#### workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

### *class* zenml.models.v2.core.run_metadata.RunMetadataResponseResources(\*\*extra_data: Any)

Bases: [`WorkspaceScopedResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseResources)

Class for all resource models associated with the run metadata entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## zenml.models.v2.core.run_template module

Models representing pipeline templates.

### *class* zenml.models.v2.core.run_template.RunTemplateFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None, tag: str | None = None, name: str | None = None, workspace_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, user_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, pipeline_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, build_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, stack_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, code_repository_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None)

Bases: [`WorkspaceScopedTaggableFilter`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedTaggableFilter)

Model for filtering of run templates.

#### FILTER_EXCLUDE_FIELDS *: ClassVar[List[str]]* *= ['sort_by', 'page', 'size', 'logical_operator', 'scope_workspace', 'tag', 'code_repository_id', 'stack_id', 'build_idpipeline_id']*

#### build_id *: UUID | str | None*

#### code_repository_id *: UUID | str | None*

#### created *: datetime | str | None*

#### get_custom_filters() → List[ColumnElement[bool]]

Get custom filters.

Returns:
: A list of custom filters.

#### id *: UUID | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'build_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Build associated with the template.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'code_repository_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Code repository associated with the template.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Name of the run template.'), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'pipeline_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Pipeline associated with the template.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'stack_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Stack associated with the template.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'tag': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Tag to apply to the filter query.'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'user_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='User that created the template.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'workspace_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Workspace associated with the template.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str | None*

#### page *: int*

#### pipeline_id *: UUID | str | None*

#### scope_workspace *: UUID | None*

#### size *: int*

#### sort_by *: str*

#### stack_id *: UUID | str | None*

#### tag *: str | None*

#### updated *: datetime | str | None*

#### user_id *: UUID | str | None*

#### workspace_id *: UUID | str | None*

### *class* zenml.models.v2.core.run_template.RunTemplateRequest(\*, user: UUID, workspace: UUID, name: Annotated[str, MaxLen(max_length=255)], description: Annotated[str | None, MaxLen(max_length=65535)] = None, source_deployment_id: UUID, tags: List[str] | None = None)

Bases: [`WorkspaceScopedRequest`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedRequest)

Request model for run templates.

#### description *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The description of the run template.', metadata=[MaxLen(max_length=65535)]), 'name': FieldInfo(annotation=str, required=True, title='The name of the run template.', metadata=[MaxLen(max_length=255)]), 'source_deployment_id': FieldInfo(annotation=UUID, required=True, title='The deployment that should be the base of the created template.'), 'tags': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None, title='Tags of the run template.'), 'user': FieldInfo(annotation=UUID, required=True, title='The id of the user that created this resource.'), 'workspace': FieldInfo(annotation=UUID, required=True, title='The workspace to which this resource belongs.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### source_deployment_id *: UUID*

#### tags *: List[str] | None*

#### user *: UUID*

#### workspace *: UUID*

### *class* zenml.models.v2.core.run_template.RunTemplateResponse(\*, body: [RunTemplateResponseBody](#zenml.models.v2.core.run_template.RunTemplateResponseBody) | None = None, metadata: [RunTemplateResponseMetadata](#zenml.models.v2.core.run_template.RunTemplateResponseMetadata) | None = None, resources: [RunTemplateResponseResources](#zenml.models.v2.core.run_template.RunTemplateResponseResources) | None = None, id: UUID, permission_denied: bool = False, name: Annotated[str, MaxLen(max_length=255)])

Bases: `WorkspaceScopedResponse[RunTemplateResponseBody, RunTemplateResponseMetadata, RunTemplateResponseResources]`

Response model for run templates.

#### body *: 'AnyBody' | None*

#### *property* build *: [PipelineBuildResponse](#zenml.models.v2.core.pipeline_build.PipelineBuildResponse) | None*

The build property.

Returns:
: the value of the property.

#### *property* code_reference *: [CodeReferenceResponse](#zenml.models.v2.core.code_reference.CodeReferenceResponse) | None*

The code_reference property.

Returns:
: the value of the property.

#### *property* config_schema *: Dict[str, Any] | None*

The config_schema property.

Returns:
: the value of the property.

#### *property* config_template *: Dict[str, Any] | None*

The config_template property.

Returns:
: the value of the property.

#### *property* description *: str | None*

The description property.

Returns:
: the value of the property.

#### get_hydrated_version() → [RunTemplateResponse](#zenml.models.v2.core.run_template.RunTemplateResponse)

Return the hydrated version of this run template.

Returns:
: The hydrated run template.

#### id *: UUID*

#### *property* latest_run_id *: UUID | None*

The latest_run_id property.

Returns:
: the value of the property.

#### *property* latest_run_status *: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus) | None*

The latest_run_status property.

Returns:
: the value of the property.

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[RunTemplateResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[RunTemplateResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the run template.', metadata=[MaxLen(max_length=255)]), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[RunTemplateResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str*

#### permission_denied *: bool*

#### *property* pipeline *: [PipelineResponse](#zenml.models.v2.core.pipeline.PipelineResponse) | None*

The pipeline property.

Returns:
: the value of the property.

#### *property* pipeline_spec *: [PipelineSpec](zenml.config.md#zenml.config.pipeline_spec.PipelineSpec) | None*

The pipeline_spec property.

Returns:
: the value of the property.

#### resources *: 'AnyResources' | None*

#### *property* runnable *: bool*

The runnable property.

Returns:
: the value of the property.

#### *property* source_deployment *: [PipelineDeploymentResponse](#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentResponse) | None*

The source_deployment property.

Returns:
: the value of the property.

#### *property* tags *: List[[TagResponse](#zenml.models.v2.core.tag.TagResponse)]*

The tags property.

Returns:
: the value of the property.

### *class* zenml.models.v2.core.run_template.RunTemplateResponseBody(\*, created: datetime, updated: datetime, user: [UserResponse](#zenml.models.v2.core.user.UserResponse) | None = None, runnable: bool, latest_run_id: UUID | None = None, latest_run_status: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus) | None = None)

Bases: [`WorkspaceScopedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseBody)

Response body for run templates.

#### created *: datetime*

#### latest_run_id *: UUID | None*

#### latest_run_status *: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus) | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'latest_run_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The ID of the latest run of the run template.'), 'latest_run_status': FieldInfo(annotation=Union[ExecutionStatus, NoneType], required=False, default=None, title='The status of the latest run of the run template.'), 'runnable': FieldInfo(annotation=bool, required=True, title='If a run can be started from the template.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.'), 'user': FieldInfo(annotation=Union[UserResponse, NoneType], required=False, default=None, title='The user who created this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### runnable *: bool*

#### updated *: datetime*

#### user *: 'UserResponse' | None*

### *class* zenml.models.v2.core.run_template.RunTemplateResponseMetadata(\*, workspace: [WorkspaceResponse](#zenml.models.v2.core.workspace.WorkspaceResponse), description: str | None = None, pipeline_spec: [PipelineSpec](zenml.config.md#zenml.config.pipeline_spec.PipelineSpec) | None = None, config_template: Dict[str, Any] | None = None, config_schema: Dict[str, Any] | None = None)

Bases: [`WorkspaceScopedResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseMetadata)

Response metadata for run templates.

#### config_schema *: Dict[str, Any] | None*

#### config_template *: Dict[str, Any] | None*

#### description *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config_schema': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, title='Run configuration schema.'), 'config_template': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, title='Run configuration template.'), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The description of the run template.'), 'pipeline_spec': FieldInfo(annotation=Union[PipelineSpec, NoneType], required=False, default=None, title='The spec of the pipeline.'), 'workspace': FieldInfo(annotation=WorkspaceResponse, required=True, title='The workspace of this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### pipeline_spec *: [PipelineSpec](zenml.config.md#zenml.config.pipeline_spec.PipelineSpec) | None*

#### workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

### *class* zenml.models.v2.core.run_template.RunTemplateResponseResources(\*, source_deployment: [PipelineDeploymentResponse](#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentResponse) | None = None, pipeline: [PipelineResponse](#zenml.models.v2.core.pipeline.PipelineResponse) | None = None, build: [PipelineBuildResponse](#zenml.models.v2.core.pipeline_build.PipelineBuildResponse) | None = None, code_reference: [CodeReferenceResponse](#zenml.models.v2.core.code_reference.CodeReferenceResponse) | None = None, tags: List[[TagResponse](#zenml.models.v2.core.tag.TagResponse)], \*\*extra_data: Any)

Bases: [`WorkspaceScopedResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseResources)

All resource models associated with the run template.

#### build *: [PipelineBuildResponse](#zenml.models.v2.core.pipeline_build.PipelineBuildResponse) | None*

#### code_reference *: [CodeReferenceResponse](#zenml.models.v2.core.code_reference.CodeReferenceResponse) | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'build': FieldInfo(annotation=Union[PipelineBuildResponse, NoneType], required=False, default=None, title='The pipeline build associated with the template.'), 'code_reference': FieldInfo(annotation=Union[CodeReferenceResponse, NoneType], required=False, default=None, title='The code reference associated with the template.'), 'pipeline': FieldInfo(annotation=Union[PipelineResponse, NoneType], required=False, default=None, title='The pipeline associated with the template.'), 'source_deployment': FieldInfo(annotation=Union[PipelineDeploymentResponse, NoneType], required=False, default=None, title='The deployment that is the source of the template.'), 'tags': FieldInfo(annotation=List[TagResponse], required=True, title='Tags associated with the run template.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### pipeline *: [PipelineResponse](#zenml.models.v2.core.pipeline.PipelineResponse) | None*

#### source_deployment *: [PipelineDeploymentResponse](#zenml.models.v2.core.pipeline_deployment.PipelineDeploymentResponse) | None*

#### tags *: List[[TagResponse](#zenml.models.v2.core.tag.TagResponse)]*

### *class* zenml.models.v2.core.run_template.RunTemplateUpdate(\*, name: Annotated[str | None, MaxLen(max_length=255)] = None, description: Annotated[str | None, MaxLen(max_length=65535)] = None, add_tags: List[str] | None = None, remove_tags: List[str] | None = None)

Bases: [`BaseUpdate`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseUpdate)

Run template update model.

#### add_tags *: List[str] | None*

#### description *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'add_tags': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None, title='New tags to add to the run template.'), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The description of the run template.', metadata=[MaxLen(max_length=65535)]), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The name of the run template.', metadata=[MaxLen(max_length=255)]), 'remove_tags': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None, title='Tags to remove from the run template.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

#### remove_tags *: List[str] | None*

## zenml.models.v2.core.schedule module

Models representing schedules.

### *class* zenml.models.v2.core.schedule.ScheduleFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None, workspace_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, user_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, pipeline_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, orchestrator_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, active: bool | None = None, cron_expression: str | None = None, start_time: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, end_time: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, interval_second: float | None = None, catchup: bool | None = None, name: str | None = None, run_once_start_time: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None)

Bases: [`WorkspaceScopedFilter`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedFilter)

Model to enable advanced filtering of all Users.

#### active *: bool | None*

#### catchup *: bool | None*

#### created *: datetime | str | None*

#### cron_expression *: str | None*

#### end_time *: datetime | str | None*

#### id *: UUID | str | None*

#### interval_second *: float | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'active': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, description='If the schedule is active'), 'catchup': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, description='Whether or not the schedule is set to catchup past missed events'), 'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'cron_expression': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The cron expression, describing the schedule'), 'end_time': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='End time', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'interval_second': FieldInfo(annotation=Union[float, NoneType], required=False, default=None, description='The repetition interval in seconds'), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Name of the schedule'), 'orchestrator_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Orchestrator that the schedule is attached to.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'pipeline_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Pipeline that the schedule is attached to.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'run_once_start_time': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='The time at which the schedule should run once', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'start_time': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Start time', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'user_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='User that created the schedule', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'workspace_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Workspace scope of the schedule.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str | None*

#### orchestrator_id *: UUID | str | None*

#### page *: int*

#### pipeline_id *: UUID | str | None*

#### run_once_start_time *: datetime | str | None*

#### scope_workspace *: UUID | None*

#### size *: int*

#### sort_by *: str*

#### start_time *: datetime | str | None*

#### updated *: datetime | str | None*

#### user_id *: UUID | str | None*

#### workspace_id *: UUID | str | None*

### *class* zenml.models.v2.core.schedule.ScheduleRequest(\*, user: UUID, workspace: UUID, name: str, active: bool, cron_expression: str | None = None, start_time: datetime | None = None, end_time: datetime | None = None, interval_second: timedelta | None = None, catchup: bool = False, run_once_start_time: datetime | None = None, orchestrator_id: UUID | None, pipeline_id: UUID | None)

Bases: [`WorkspaceScopedRequest`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedRequest)

Request model for schedules.

#### active *: bool*

#### catchup *: bool*

#### cron_expression *: str | None*

#### end_time *: datetime | None*

#### interval_second *: timedelta | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'active': FieldInfo(annotation=bool, required=True), 'catchup': FieldInfo(annotation=bool, required=False, default=False), 'cron_expression': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'end_time': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'interval_second': FieldInfo(annotation=Union[timedelta, NoneType], required=False, default=None), 'name': FieldInfo(annotation=str, required=True), 'orchestrator_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'pipeline_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'run_once_start_time': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'start_time': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'user': FieldInfo(annotation=UUID, required=True, title='The id of the user that created this resource.'), 'workspace': FieldInfo(annotation=UUID, required=True, title='The workspace to which this resource belongs.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### orchestrator_id *: UUID | None*

#### pipeline_id *: UUID | None*

#### run_once_start_time *: datetime | None*

#### start_time *: datetime | None*

#### user *: UUID*

#### workspace *: UUID*

### *class* zenml.models.v2.core.schedule.ScheduleResponse(\*, body: [ScheduleResponseBody](#zenml.models.v2.core.schedule.ScheduleResponseBody) | None = None, metadata: [ScheduleResponseMetadata](#zenml.models.v2.core.schedule.ScheduleResponseMetadata) | None = None, resources: [ScheduleResponseResources](#zenml.models.v2.core.schedule.ScheduleResponseResources) | None = None, id: UUID, permission_denied: bool = False, name: Annotated[str, MaxLen(max_length=255)])

Bases: `WorkspaceScopedResponse[ScheduleResponseBody, ScheduleResponseMetadata, ScheduleResponseResources]`

Response model for schedules.

#### *property* active *: bool*

The active property.

Returns:
: the value of the property.

#### body *: 'AnyBody' | None*

#### *property* catchup *: bool*

The catchup property.

Returns:
: the value of the property.

#### *property* cron_expression *: str | None*

The cron_expression property.

Returns:
: the value of the property.

#### *property* end_time *: datetime | None*

The end_time property.

Returns:
: the value of the property.

#### get_hydrated_version() → [ScheduleResponse](#zenml.models.v2.core.schedule.ScheduleResponse)

Get the hydrated version of this schedule.

Returns:
: an instance of the same entity with the metadata field attached.

#### id *: UUID*

#### *property* interval_second *: timedelta | None*

The interval_second property.

Returns:
: the value of the property.

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[ScheduleResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[ScheduleResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='Name of this schedule.', metadata=[MaxLen(max_length=255)]), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[ScheduleResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str*

#### *property* orchestrator_id *: UUID | None*

The orchestrator_id property.

Returns:
: the value of the property.

#### permission_denied *: bool*

#### *property* pipeline_id *: UUID | None*

The pipeline_id property.

Returns:
: the value of the property.

#### resources *: 'AnyResources' | None*

#### *property* run_once_start_time *: datetime | None*

The run_once_start_time property.

Returns:
: the value of the property.

#### *property* start_time *: datetime | None*

The start_time property.

Returns:
: the value of the property.

#### *property* utc_end_time *: str | None*

Optional ISO-formatted string of the UTC end time.

Returns:
: Optional ISO-formatted string of the UTC end time.

#### *property* utc_start_time *: str | None*

Optional ISO-formatted string of the UTC start time.

Returns:
: Optional ISO-formatted string of the UTC start time.

### *class* zenml.models.v2.core.schedule.ScheduleResponseBody(\*, created: datetime, updated: datetime, user: [UserResponse](#zenml.models.v2.core.user.UserResponse) | None = None, active: bool, cron_expression: str | None = None, start_time: datetime | None = None, end_time: datetime | None = None, interval_second: timedelta | None = None, catchup: bool = False, run_once_start_time: datetime | None = None)

Bases: [`WorkspaceScopedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseBody)

Response body for schedules.

#### active *: bool*

#### catchup *: bool*

#### created *: datetime*

#### cron_expression *: str | None*

#### end_time *: datetime | None*

#### interval_second *: timedelta | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'active': FieldInfo(annotation=bool, required=True), 'catchup': FieldInfo(annotation=bool, required=False, default=False), 'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'cron_expression': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'end_time': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'interval_second': FieldInfo(annotation=Union[timedelta, NoneType], required=False, default=None), 'run_once_start_time': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'start_time': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.'), 'user': FieldInfo(annotation=Union[UserResponse, NoneType], required=False, default=None, title='The user who created this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### run_once_start_time *: datetime | None*

#### start_time *: datetime | None*

#### updated *: datetime*

#### user *: 'UserResponse' | None*

### *class* zenml.models.v2.core.schedule.ScheduleResponseMetadata(\*, workspace: [WorkspaceResponse](#zenml.models.v2.core.workspace.WorkspaceResponse), orchestrator_id: UUID | None, pipeline_id: UUID | None)

Bases: [`WorkspaceScopedResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseMetadata)

Response metadata for schedules.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'orchestrator_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'pipeline_id': FieldInfo(annotation=Union[UUID, NoneType], required=True), 'workspace': FieldInfo(annotation=WorkspaceResponse, required=True, title='The workspace of this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### orchestrator_id *: UUID | None*

#### pipeline_id *: UUID | None*

#### workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

### *class* zenml.models.v2.core.schedule.ScheduleResponseResources(\*\*extra_data: Any)

Bases: [`WorkspaceScopedResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseResources)

Class for all resource models associated with the schedule entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.schedule.ScheduleUpdate(\*, name: str | None = None, active: bool | None = None, cron_expression: str | None = None, start_time: datetime | None = None, end_time: datetime | None = None, interval_second: timedelta | None = None, catchup: bool | None = None, run_once_start_time: datetime | None = None, orchestrator_id: UUID | None = None, pipeline_id: UUID | None = None)

Bases: [`BaseUpdate`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseUpdate)

Update model for schedules.

#### active *: bool | None*

#### catchup *: bool | None*

#### cron_expression *: str | None*

#### end_time *: datetime | None*

#### interval_second *: timedelta | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'active': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'catchup': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None), 'cron_expression': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'end_time': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'interval_second': FieldInfo(annotation=Union[timedelta, NoneType], required=False, default=None), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'orchestrator_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'pipeline_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'run_once_start_time': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'start_time': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

#### orchestrator_id *: UUID | None*

#### pipeline_id *: UUID | None*

#### run_once_start_time *: datetime | None*

#### start_time *: datetime | None*

## zenml.models.v2.core.secret module

Models representing secrets.

### *class* zenml.models.v2.core.secret.SecretFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None, name: str | None = None, scope: Annotated[[SecretScope](zenml.md#zenml.enums.SecretScope) | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, workspace_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, user_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None)

Bases: [`WorkspaceScopedFilter`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedFilter)

Model to enable advanced filtering of all Secrets.

#### FILTER_EXCLUDE_FIELDS *: ClassVar[List[str]]* *= ['sort_by', 'page', 'size', 'logical_operator', 'scope_workspace', 'values']*

#### created *: datetime | str | None*

#### id *: UUID | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Name of the secret'), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'scope': FieldInfo(annotation=Union[SecretScope, str, NoneType], required=False, default=None, description='Scope in which to filter secrets', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'user_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='User that created the Secret', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'workspace_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Workspace of the Secret', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str | None*

#### page *: int*

#### scope *: [SecretScope](zenml.md#zenml.enums.SecretScope) | str | None*

#### scope_workspace *: UUID | None*

#### secret_matches(secret: [SecretResponse](#zenml.models.v2.core.secret.SecretResponse)) → bool

Checks if a secret matches the filter criteria.

Args:
: secret: The secret to check.

Returns:
: True if the secret matches the filter criteria, False otherwise.

#### size *: int*

#### sort_by *: str*

#### sort_secrets(secrets: List[[SecretResponse](#zenml.models.v2.core.secret.SecretResponse)]) → List[[SecretResponse](#zenml.models.v2.core.secret.SecretResponse)]

Sorts a list of secrets according to the filter criteria.

Args:
: secrets: The list of secrets to sort.

Returns:
: The sorted list of secrets.

#### updated *: datetime | str | None*

#### user_id *: UUID | str | None*

#### workspace_id *: UUID | str | None*

### *class* zenml.models.v2.core.secret.SecretRequest(\*, user: ~uuid.UUID, workspace: ~uuid.UUID, name: ~typing.Annotated[str, ~annotated_types.MaxLen(max_length=255)], scope: ~zenml.enums.SecretScope = SecretScope.WORKSPACE, values: ~typing.Dict[str, ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)] | None] = None)

Bases: [`WorkspaceScopedRequest`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedRequest)

Request models for secrets.

#### ANALYTICS_FIELDS *: ClassVar[List[str]]* *= ['scope']*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'name': FieldInfo(annotation=str, required=True, title='The name of the secret.', metadata=[MaxLen(max_length=255)]), 'scope': FieldInfo(annotation=SecretScope, required=False, default=<SecretScope.WORKSPACE: 'workspace'>, title='The scope of the secret.'), 'user': FieldInfo(annotation=UUID, required=True, title='The id of the user that created this resource.'), 'values': FieldInfo(annotation=Dict[str, Union[Annotated[SecretStr, PlainSerializer], NoneType]], required=False, default_factory=dict, title='The values stored in this secret.'), 'workspace': FieldInfo(annotation=UUID, required=True, title='The workspace to which this resource belongs.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### scope *: [SecretScope](zenml.md#zenml.enums.SecretScope)*

#### *property* secret_values *: Dict[str, str]*

A dictionary with all un-obfuscated values stored in this secret.

The values are returned as strings, not SecretStr. If a value is
None, it is not included in the returned dictionary. This is to enable
the use of None values in the update model to indicate that a secret
value should be deleted.

Returns:
: A dictionary containing the secret’s values.

#### user *: UUID*

#### values *: <lambda>, return_type=PydanticUndefined, when_used=json)] | None]*

#### workspace *: UUID*

### *class* zenml.models.v2.core.secret.SecretResponse(\*, body: [SecretResponseBody](#zenml.models.v2.core.secret.SecretResponseBody) | None = None, metadata: [SecretResponseMetadata](#zenml.models.v2.core.secret.SecretResponseMetadata) | None = None, resources: [SecretResponseResources](#zenml.models.v2.core.secret.SecretResponseResources) | None = None, id: UUID, permission_denied: bool = False, name: Annotated[str, MaxLen(max_length=255)])

Bases: `WorkspaceScopedResponse[SecretResponseBody, SecretResponseMetadata, SecretResponseResources]`

Response model for secrets.

#### ANALYTICS_FIELDS *: ClassVar[List[str]]* *= ['scope']*

#### add_secret(key: str, value: str) → None

Adds a secret value to the secret.

Args:
: key: The key of the secret value.
  value: The secret value.

#### body *: 'AnyBody' | None*

#### get_hydrated_version() → [SecretResponse](#zenml.models.v2.core.secret.SecretResponse)

Get the hydrated version of this workspace.

Returns:
: an instance of the same entity with the metadata field attached.

#### *property* has_missing_values *: bool*

Returns True if the secret has missing values (i.e. None).

Values can be missing from a secret for example if the user retrieves a
secret but does not have the permission to view the secret values.

Returns:
: True if the secret has any values set to None.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[SecretResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[SecretResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the secret.', metadata=[MaxLen(max_length=255)]), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[SecretResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str*

#### permission_denied *: bool*

#### remove_secret(key: str) → None

Removes a secret value from the secret.

Args:
: key: The key of the secret value.

#### remove_secrets() → None

Removes all secret values from the secret but keep the keys.

#### resources *: 'AnyResources' | None*

#### *property* scope *: [SecretScope](zenml.md#zenml.enums.SecretScope)*

The scope property.

Returns:
: the value of the property.

#### *property* secret_values *: Dict[str, str]*

A dictionary with all un-obfuscated values stored in this secret.

The values are returned as strings, not SecretStr. If a value is
None, it is not included in the returned dictionary. This is to enable
the use of None values in the update model to indicate that a secret
value should be deleted.

Returns:
: A dictionary containing the secret’s values.

#### set_secrets(values: Dict[str, str]) → None

Sets the secret values of the secret.

Args:
: values: The secret values to set.

#### *property* values *: Dict[str, SecretStr | None]*

The values property.

Returns:
: the value of the property.

### *class* zenml.models.v2.core.secret.SecretResponseBody(\*, created: ~datetime.datetime, updated: ~datetime.datetime, user: ~zenml.models.v2.core.user.UserResponse | None = None, scope: ~zenml.enums.SecretScope = SecretScope.WORKSPACE, values: ~typing.Dict[str, ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)] | None] = None)

Bases: [`WorkspaceScopedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseBody)

Response body for secrets.

#### created *: datetime*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'scope': FieldInfo(annotation=SecretScope, required=False, default=<SecretScope.WORKSPACE: 'workspace'>, title='The scope of the secret.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.'), 'user': FieldInfo(annotation=Union[UserResponse, NoneType], required=False, default=None, title='The user who created this resource.'), 'values': FieldInfo(annotation=Dict[str, Union[Annotated[SecretStr, PlainSerializer], NoneType]], required=False, default_factory=dict, title='The values stored in this secret.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### scope *: [SecretScope](zenml.md#zenml.enums.SecretScope)*

#### updated *: datetime*

#### user *: 'UserResponse' | None*

#### values *: <lambda>, return_type=PydanticUndefined, when_used=json)] | None]*

### *class* zenml.models.v2.core.secret.SecretResponseMetadata(\*, workspace: [WorkspaceResponse](#zenml.models.v2.core.workspace.WorkspaceResponse))

Bases: [`WorkspaceScopedResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseMetadata)

Response metadata for secrets.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'workspace': FieldInfo(annotation=WorkspaceResponse, required=True, title='The workspace of this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

### *class* zenml.models.v2.core.secret.SecretResponseResources(\*\*extra_data: Any)

Bases: [`WorkspaceScopedResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseResources)

Class for all resource models associated with the secret entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.secret.SecretUpdate(\*, name: ~typing.Annotated[str | None, ~annotated_types.MaxLen(max_length=255)] = None, scope: ~zenml.enums.SecretScope | None = None, values: ~typing.Dict[str, ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)] | None] | None = None)

Bases: [`BaseUpdate`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseUpdate)

Secret update model.

#### ANALYTICS_FIELDS *: ClassVar[List[str]]* *= ['scope']*

#### get_secret_values_update() → Dict[str, str | None]

Returns a dictionary with the secret values to update.

Returns:
: A dictionary with the secret values to update.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The name of the secret.', metadata=[MaxLen(max_length=255)]), 'scope': FieldInfo(annotation=Union[SecretScope, NoneType], required=False, default=None, title='The scope of the secret.'), 'values': FieldInfo(annotation=Union[Dict[str, Union[Annotated[SecretStr, PlainSerializer], NoneType]], NoneType], required=False, default=None, title='The values stored in this secret.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

#### scope *: [SecretScope](zenml.md#zenml.enums.SecretScope) | None*

#### values *: <lambda>, return_type=PydanticUndefined, when_used=json)] | None] | None*

## zenml.models.v2.core.server_settings module

Models representing server settings stored in the database.

### *class* zenml.models.v2.core.server_settings.ServerActivationRequest(\*, server_name: str | None = None, logo_url: str | None = None, enable_analytics: bool | None = None, display_announcements: bool | None = None, display_updates: bool | None = None, admin_username: str | None = None, admin_password: str | None = None)

Bases: [`ServerSettingsUpdate`](#zenml.models.v2.core.server_settings.ServerSettingsUpdate)

Model for activating the server.

#### admin_password *: str | None*

#### admin_username *: str | None*

#### display_announcements *: bool | None*

#### display_updates *: bool | None*

#### enable_analytics *: bool | None*

#### logo_url *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'admin_password': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The password of the default admin account to create. Leave empty to skip creating the default admin account.'), 'admin_username': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The username of the default admin account to create. Leave empty to skip creating the default admin account.'), 'display_announcements': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, title='Whether to display announcements about ZenML in the dashboard.'), 'display_updates': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, title='Whether to display notifications about ZenML updates in the dashboard.'), 'enable_analytics': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, title='Whether to enable analytics for the server.'), 'logo_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The logo URL of the server.'), 'server_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The name of the server.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### server_name *: str | None*

### *class* zenml.models.v2.core.server_settings.ServerSettingsResponse(\*, body: [ServerSettingsResponseBody](#zenml.models.v2.core.server_settings.ServerSettingsResponseBody) | None = None, metadata: [ServerSettingsResponseMetadata](#zenml.models.v2.core.server_settings.ServerSettingsResponseMetadata) | None = None, resources: [ServerSettingsResponseResources](#zenml.models.v2.core.server_settings.ServerSettingsResponseResources) | None = None)

Bases: `BaseResponse[ServerSettingsResponseBody, ServerSettingsResponseMetadata, ServerSettingsResponseResources]`

Response model for server settings.

#### *property* active *: bool*

The active property.

Returns:
: the value of the property.

#### body *: AnyBody | None*

#### *property* display_announcements *: bool | None*

The display_announcements property.

Returns:
: the value of the property.

#### *property* display_updates *: bool | None*

The display_updates property.

Returns:
: the value of the property.

#### *property* enable_analytics *: bool*

The enable_analytics property.

Returns:
: the value of the property.

#### get_hydrated_version() → [ServerSettingsResponse](#zenml.models.v2.core.server_settings.ServerSettingsResponse)

Get the hydrated version of the server settings.

Returns:
: An instance of the same entity with the metadata field attached.

#### *property* last_user_activity *: datetime*

The last_user_activity property.

Returns:
: the value of the property.

#### *property* logo_url *: str | None*

The logo_url property.

Returns:
: the value of the property.

#### metadata *: AnyMetadata | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[ServerSettingsResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'metadata': FieldInfo(annotation=Union[ServerSettingsResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'resources': FieldInfo(annotation=Union[ServerSettingsResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### resources *: AnyResources | None*

#### *property* server_id *: UUID*

The server_id property.

Returns:
: the value of the property.

#### *property* server_name *: str*

The server_name property.

Returns:
: the value of the property.

#### *property* updated *: datetime*

The updated property.

Returns:
: the value of the property.

### *class* zenml.models.v2.core.server_settings.ServerSettingsResponseBody(\*, server_id: UUID, server_name: str, logo_url: str | None = None, active: bool, enable_analytics: bool, display_announcements: bool | None, display_updates: bool | None, last_user_activity: datetime, updated: datetime)

Bases: [`BaseResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseBody)

Response body for server settings.

#### active *: bool*

#### display_announcements *: bool | None*

#### display_updates *: bool | None*

#### enable_analytics *: bool*

#### last_user_activity *: datetime*

#### logo_url *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'active': FieldInfo(annotation=bool, required=True, title='Whether the server has been activated or not.'), 'display_announcements': FieldInfo(annotation=Union[bool, NoneType], required=True, title='Whether to display announcements about ZenML in the dashboard.'), 'display_updates': FieldInfo(annotation=Union[bool, NoneType], required=True, title='Whether to display notifications about ZenML updates in the dashboard.'), 'enable_analytics': FieldInfo(annotation=bool, required=True, title='Whether analytics are enabled for the server.'), 'last_user_activity': FieldInfo(annotation=datetime, required=True, title='The timestamp when the last user activity was detected.'), 'logo_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The logo URL of the server.'), 'server_id': FieldInfo(annotation=UUID, required=True, title='The unique server id.'), 'server_name': FieldInfo(annotation=str, required=True, title='The name of the server.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### server_id *: UUID*

#### server_name *: str*

#### updated *: datetime*

### *class* zenml.models.v2.core.server_settings.ServerSettingsResponseMetadata

Bases: [`BaseResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseMetadata)

Response metadata for server settings.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.server_settings.ServerSettingsResponseResources(\*\*extra_data: Any)

Bases: [`BaseResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseResources)

Response resources for server settings.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.server_settings.ServerSettingsUpdate(\*, server_name: str | None = None, logo_url: str | None = None, enable_analytics: bool | None = None, display_announcements: bool | None = None, display_updates: bool | None = None)

Bases: [`BaseZenModel`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseZenModel)

Model for updating server settings.

#### display_announcements *: bool | None*

#### display_updates *: bool | None*

#### enable_analytics *: bool | None*

#### logo_url *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'display_announcements': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, title='Whether to display announcements about ZenML in the dashboard.'), 'display_updates': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, title='Whether to display notifications about ZenML updates in the dashboard.'), 'enable_analytics': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, title='Whether to enable analytics for the server.'), 'logo_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The logo URL of the server.'), 'server_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The name of the server.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### server_name *: str | None*

## zenml.models.v2.core.service module

Models representing Services.

### *class* zenml.models.v2.core.service.ServiceFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None, name: str | None = None, workspace_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, user_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, type: str | None = None, flavor: str | None = None, config: bytes | None = None, pipeline_name: str | None = None, pipeline_step_name: str | None = None, running: bool | None = None, model_version_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, pipeline_run_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None)

Bases: [`WorkspaceScopedFilter`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedFilter)

Model to enable advanced filtering of services.

The Service needs additional scoping. As such the \_scope_user field
can be set to the user that is doing the filtering. The
generate_filter() method of the baseclass is overwritten to include the
scoping.

#### CLI_EXCLUDE_FIELDS *: ClassVar[List[str]]* *= ['scope_workspace', 'workspace_id', 'user_id', 'flavor', 'type', 'pipeline_step_name', 'running', 'pipeline_name']*

#### FILTER_EXCLUDE_FIELDS *: ClassVar[List[str]]* *= ['sort_by', 'page', 'size', 'logical_operator', 'scope_workspace', 'flavor', 'type', 'pipeline_step_name', 'running', 'pipeline_name', 'config']*

#### config *: bytes | None*

#### created *: datetime | str | None*

#### flavor *: str | None*

#### generate_filter(table: Type[SQLModel]) → ColumnElement[bool]

Generate the filter for the query.

Services can be scoped by type to narrow the search.

Args:
: table: The Table that is being queried from.

Returns:
: The filter expression for the query.

#### id *: UUID | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config': FieldInfo(annotation=Union[bytes, NoneType], required=False, default=None, description='Config of the service. Use this to filter services by their config.'), 'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'flavor': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Flavor of the service. Use this to filter services by their flavor.'), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'model_version_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='By the model version this service is attached to.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Name of the service. Use this to filter services by their name.'), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'pipeline_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Pipeline name responsible for deploying the service'), 'pipeline_run_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='By the pipeline run this service is attached to.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'pipeline_step_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Pipeline step name responsible for deploying the service'), 'running': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, description='Whether the service is running'), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Type of the service. Filter services by their type.'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'user_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='User of the service', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'workspace_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Workspace of the service', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### model_version_id *: UUID | str | None*

#### name *: str | None*

#### page *: int*

#### pipeline_name *: str | None*

#### pipeline_run_id *: UUID | str | None*

#### pipeline_step_name *: str | None*

#### running *: bool | None*

#### scope_workspace *: UUID | None*

#### set_flavor(flavor: str) → None

Set the flavor of the service.

Args:
: flavor: The flavor of the service.

#### set_type(type: str) → None

Set the type of the service.

Args:
: type: The type of the service.

#### size *: int*

#### sort_by *: str*

#### type *: str | None*

#### updated *: datetime | str | None*

#### user_id *: UUID | str | None*

#### workspace_id *: UUID | str | None*

### *class* zenml.models.v2.core.service.ServiceRequest(\*, user: UUID, workspace: UUID, name: Annotated[str, MaxLen(max_length=255)], service_type: [ServiceType](zenml.services.md#zenml.services.service_type.ServiceType), service_source: str | None = None, admin_state: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) | None = None, config: Dict[str, Any], labels: Dict[str, str] | None = None, status: Dict[str, Any] | None = None, endpoint: Dict[str, Any] | None = None, prediction_url: str | None = None, health_check_url: str | None = None, model_version_id: UUID | None = None, pipeline_run_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None)

Bases: [`WorkspaceScopedRequest`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedRequest)

Request model for services.

#### admin_state *: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) | None*

#### config *: Dict[str, Any]*

#### endpoint *: Dict[str, Any] | None*

#### health_check_url *: str | None*

#### labels *: Dict[str, str] | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'admin_state': FieldInfo(annotation=Union[ServiceState, NoneType], required=False, default=None, title='The admin state of the service.', description='The administrative state of the service, e.g., ACTIVE, INACTIVE.'), 'config': FieldInfo(annotation=Dict[str, Any], required=True, title='The service config.', description='A dictionary containing configuration parameters for the service.'), 'endpoint': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, title='The service endpoint.'), 'health_check_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The service health check URL.'), 'labels': FieldInfo(annotation=Union[Dict[str, str], NoneType], required=False, default=None, title='The service labels.'), 'model_version_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The model version id linked to the service.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the service.', metadata=[MaxLen(max_length=255)]), 'pipeline_run_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='By the event source this trigger is attached to.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'prediction_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The service endpoint URL.'), 'service_source': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The class of the service.', description='The fully qualified class name of the service implementation.'), 'service_type': FieldInfo(annotation=ServiceType, required=True, title='The type of the service.'), 'status': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, title='The status of the service.'), 'user': FieldInfo(annotation=UUID, required=True, title='The id of the user that created this resource.'), 'workspace': FieldInfo(annotation=UUID, required=True, title='The workspace to which this resource belongs.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_version_id *: UUID | None*

#### name *: str*

#### pipeline_run_id *: UUID | str | None*

#### prediction_url *: str | None*

#### service_source *: str | None*

#### service_type *: [ServiceType](zenml.services.md#zenml.services.service_type.ServiceType)*

#### status *: Dict[str, Any] | None*

#### user *: UUID*

#### workspace *: UUID*

### *class* zenml.models.v2.core.service.ServiceResponse(\*, body: [ServiceResponseBody](#zenml.models.v2.core.service.ServiceResponseBody) | None = None, metadata: [ServiceResponseMetadata](#zenml.models.v2.core.service.ServiceResponseMetadata) | None = None, resources: [ServiceResponseResources](#zenml.models.v2.core.service.ServiceResponseResources) | None = None, id: UUID, permission_denied: bool = False, name: Annotated[str, MaxLen(max_length=255)])

Bases: `WorkspaceScopedResponse[ServiceResponseBody, ServiceResponseMetadata, ServiceResponseResources]`

Response model for services.

#### *property* admin_state *: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) | None*

The admin_state property.

Returns:
: the value of the property.

#### body *: 'AnyBody' | None*

#### *property* config *: Dict[str, Any]*

The config property.

Returns:
: the value of the property.

#### *property* created *: datetime*

The created property.

Returns:
: the value of the property.

#### *property* endpoint *: Dict[str, Any] | None*

The endpoint property.

Returns:
: the value of the property.

#### get_hydrated_version() → [ServiceResponse](#zenml.models.v2.core.service.ServiceResponse)

Get the hydrated version of this artifact.

Returns:
: an instance of the same entity with the metadata field attached.

#### *property* health_check_url *: str | None*

The health_check_url property.

Returns:
: the value of the property.

#### id *: UUID*

#### *property* labels *: Dict[str, str] | None*

The labels property.

Returns:
: the value of the property.

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[ServiceResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[ServiceResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the service.', metadata=[MaxLen(max_length=255)]), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[ServiceResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str*

#### permission_denied *: bool*

#### *property* prediction_url *: str | None*

The prediction_url property.

Returns:
: the value of the property.

#### resources *: 'AnyResources' | None*

#### *property* service_source *: str | None*

The service_source property.

Returns:
: the value of the property.

#### *property* service_type *: [ServiceType](zenml.services.md#zenml.services.service_type.ServiceType)*

The service_type property.

Returns:
: the value of the property.

#### *property* state *: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) | None*

The state property.

Returns:
: the value of the property.

#### *property* status *: Dict[str, Any] | None*

The status property.

Returns:
: the value of the property.

#### *property* updated *: datetime*

The updated property.

Returns:
: the value of the property.

### *class* zenml.models.v2.core.service.ServiceResponseBody(\*, created: datetime, updated: datetime, user: [UserResponse](#zenml.models.v2.core.user.UserResponse) | None = None, service_type: [ServiceType](zenml.services.md#zenml.services.service_type.ServiceType), labels: Dict[str, str] | None = None, state: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) | None = None)

Bases: [`WorkspaceScopedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseBody)

Response body for services.

#### created *: datetime*

#### labels *: Dict[str, str] | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this component was created.'), 'labels': FieldInfo(annotation=Union[Dict[str, str], NoneType], required=False, default=None, title='The service labels.'), 'service_type': FieldInfo(annotation=ServiceType, required=True, title='The type of the service.'), 'state': FieldInfo(annotation=Union[ServiceState, NoneType], required=False, default=None, title='The current state of the service.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this component was last updated.'), 'user': FieldInfo(annotation=Union[UserResponse, NoneType], required=False, default=None, title='The user who created this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### service_type *: [ServiceType](zenml.services.md#zenml.services.service_type.ServiceType)*

#### state *: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) | None*

#### updated *: datetime*

#### user *: 'UserResponse' | None*

### *class* zenml.models.v2.core.service.ServiceResponseMetadata(\*, workspace: [WorkspaceResponse](#zenml.models.v2.core.workspace.WorkspaceResponse), service_source: str | None, admin_state: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) | None, config: Dict[str, Any], status: Dict[str, Any] | None, endpoint: Dict[str, Any] | None = None, prediction_url: str | None = None, health_check_url: str | None = None)

Bases: [`WorkspaceScopedResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseMetadata)

Response metadata for services.

#### admin_state *: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) | None*

#### config *: Dict[str, Any]*

#### endpoint *: Dict[str, Any] | None*

#### health_check_url *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'admin_state': FieldInfo(annotation=Union[ServiceState, NoneType], required=True, title='The admin state of the service.'), 'config': FieldInfo(annotation=Dict[str, Any], required=True, title='The service config.'), 'endpoint': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, title='The service endpoint.'), 'health_check_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The service health check URL.'), 'prediction_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The service endpoint URL.'), 'service_source': FieldInfo(annotation=Union[str, NoneType], required=True, title='The class of the service.'), 'status': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=True, title='The status of the service.'), 'workspace': FieldInfo(annotation=WorkspaceResponse, required=True, title='The workspace of this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### prediction_url *: str | None*

#### service_source *: str | None*

#### status *: Dict[str, Any] | None*

#### workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

### *class* zenml.models.v2.core.service.ServiceResponseResources(\*\*extra_data: Any)

Bases: [`WorkspaceScopedResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseResources)

Class for all resource models associated with the service entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.service.ServiceUpdate(\*, name: Annotated[str | None, MaxLen(max_length=255)] = None, admin_state: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) | None = None, service_source: str | None = None, status: Dict[str, Any] | None = None, endpoint: Dict[str, Any] | None = None, prediction_url: str | None = None, health_check_url: str | None = None, labels: Dict[str, str] | None = None, model_version_id: UUID | None = None)

Bases: `BaseModel`

Update model for stack components.

#### admin_state *: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) | None*

#### endpoint *: Dict[str, Any] | None*

#### health_check_url *: str | None*

#### labels *: Dict[str, str] | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'admin_state': FieldInfo(annotation=Union[ServiceState, NoneType], required=False, default=None, title='The admin state of the service.', description='The administrative state of the service, e.g., ACTIVE, INACTIVE.'), 'endpoint': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, title='The service endpoint.'), 'health_check_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The service health check URL.'), 'labels': FieldInfo(annotation=Union[Dict[str, str], NoneType], required=False, default=None, title='The service labels.'), 'model_version_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The model version id linked to the service.'), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The name of the service.', metadata=[MaxLen(max_length=255)]), 'prediction_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The service endpoint URL.'), 'service_source': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The class of the service.', description='The fully qualified class name of the service implementation.'), 'status': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, title='The status of the service.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_version_id *: UUID | None*

#### name *: str | None*

#### prediction_url *: str | None*

#### service_source *: str | None*

#### status *: Dict[str, Any] | None*

## zenml.models.v2.core.service_account module

Models representing service accounts.

### *class* zenml.models.v2.core.service_account.ServiceAccountFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, name: str | None = None, description: str | None = None, active: Annotated[bool | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None)

Bases: [`BaseFilter`](zenml.models.v2.base.md#zenml.models.v2.base.filter.BaseFilter)

Model to enable advanced filtering of service accounts.

#### active *: bool | str | None*

#### apply_filter(query: AnyQuery, table: Type[AnySchema]) → AnyQuery

Override to filter out user accounts from the query.

Args:
: query: The query to which to apply the filter.
  table: The query table.

Returns:
: The query with filter applied.

#### created *: datetime | str | None*

#### description *: str | None*

#### id *: UUID | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'active': FieldInfo(annotation=Union[bool, str, NoneType], required=False, default=None, description='Whether the user is active', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Filter by the service account description.'), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Name of the user'), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str | None*

#### page *: int*

#### size *: int*

#### sort_by *: str*

#### updated *: datetime | str | None*

### *class* zenml.models.v2.core.service_account.ServiceAccountRequest(\*, name: Annotated[str, MaxLen(max_length=255)], description: Annotated[str | None, MaxLen(max_length=65535)] = None, active: bool)

Bases: [`BaseRequest`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseRequest)

Request model for service accounts.

#### ANALYTICS_FIELDS *: ClassVar[List[str]]* *= ['name', 'active']*

#### active *: bool*

#### description *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'active': FieldInfo(annotation=bool, required=True, title='Whether the service account is active or not.'), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='A description of the service account.', metadata=[MaxLen(max_length=65535)]), 'name': FieldInfo(annotation=str, required=True, title='The unique name for the service account.', metadata=[MaxLen(max_length=255)])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

### *class* zenml.models.v2.core.service_account.ServiceAccountResponse(\*, body: [ServiceAccountResponseBody](#zenml.models.v2.core.service_account.ServiceAccountResponseBody) | None = None, metadata: [ServiceAccountResponseMetadata](#zenml.models.v2.core.service_account.ServiceAccountResponseMetadata) | None = None, resources: [ServiceAccountResponseResources](#zenml.models.v2.core.service_account.ServiceAccountResponseResources) | None = None, id: UUID, permission_denied: bool = False, name: Annotated[str, MaxLen(max_length=255)])

Bases: `BaseIdentifiedResponse[ServiceAccountResponseBody, ServiceAccountResponseMetadata, ServiceAccountResponseResources]`

Response model for service accounts.

#### ANALYTICS_FIELDS *: ClassVar[List[str]]* *= ['name', 'active']*

#### *property* active *: bool*

The active property.

Returns:
: the value of the property.

#### body *: 'AnyBody' | None*

#### *property* description *: str*

The description property.

Returns:
: the value of the property.

#### get_hydrated_version() → [ServiceAccountResponse](#zenml.models.v2.core.service_account.ServiceAccountResponse)

Get the hydrated version of this service account.

Returns:
: an instance of the same entity with the metadata field attached.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[ServiceAccountResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[ServiceAccountResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='The unique username for the account.', metadata=[MaxLen(max_length=255)]), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[ServiceAccountResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str*

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### to_user_model() → [UserResponse](zenml.models.md#zenml.models.UserResponse)

Converts the service account to a user model.

For now, a lot of code still relies on the active user and resource
owners being a UserResponse object, which is a superset of the
ServiceAccountResponse object. We need this method to convert the
service account to a user.

Returns:
: The user model.

### *class* zenml.models.v2.core.service_account.ServiceAccountResponseBody(\*, created: datetime, updated: datetime, active: bool = False)

Bases: [`BaseDatedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseDatedResponseBody)

Response body for service accounts.

#### active *: bool*

#### created *: datetime*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'active': FieldInfo(annotation=bool, required=False, default=False, title='Whether the account is active.'), 'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### updated *: datetime*

### *class* zenml.models.v2.core.service_account.ServiceAccountResponseMetadata(\*, description: Annotated[str, MaxLen(max_length=65535)] = '')

Bases: [`BaseResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseMetadata)

Response metadata for service accounts.

#### description *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'description': FieldInfo(annotation=str, required=False, default='', title='A description of the service account.', metadata=[MaxLen(max_length=65535)])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.service_account.ServiceAccountResponseResources(\*\*extra_data: Any)

Bases: [`BaseResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseResources)

Class for all resource models associated with the service account entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.service_account.ServiceAccountUpdate(\*, name: Annotated[str | None, MaxLen(max_length=255)] = None, description: Annotated[str | None, MaxLen(max_length=65535)] = None, active: bool | None = None)

Bases: [`BaseUpdate`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseUpdate)

Update model for service accounts.

#### ANALYTICS_FIELDS *: ClassVar[List[str]]* *= ['name', 'active']*

#### active *: bool | None*

#### description *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'active': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, title='Whether the service account is active or not.'), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='A description of the service account.', metadata=[MaxLen(max_length=65535)]), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The unique name for the service account.', metadata=[MaxLen(max_length=255)])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

## zenml.models.v2.core.service_connector module

Models representing service connectors.

### *class* zenml.models.v2.core.service_connector.ServiceConnectorFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None, scope_type: str | None = None, name: str | None = None, connector_type: str | None = None, workspace_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, user_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, auth_method: str | None = None, resource_type: str | None = None, resource_id: str | None = None, labels_str: str | None = None, secret_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, labels: Dict[str, str | None] | None = None)

Bases: [`WorkspaceScopedFilter`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedFilter)

Model to enable advanced filtering of service connectors.

#### CLI_EXCLUDE_FIELDS *: ClassVar[List[str]]* *= ['scope_workspace', 'scope_type', 'labels_str', 'labels']*

#### FILTER_EXCLUDE_FIELDS *: ClassVar[List[str]]* *= ['sort_by', 'page', 'size', 'logical_operator', 'scope_workspace', 'scope_type', 'resource_type', 'labels_str', 'labels']*

#### auth_method *: str | None*

#### connector_type *: str | None*

#### created *: datetime | str | None*

#### id *: UUID | str | None*

#### labels *: Dict[str, str | None] | None*

#### labels_str *: str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'auth_method': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Filter by the authentication method configured for the connector'), 'connector_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The type of service connector to filter by'), 'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'labels': FieldInfo(annotation=Union[Dict[str, Union[str, NoneType]], NoneType], required=False, default=None, title='The labels to filter by, as a dictionary', exclude=True), 'labels_str': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Filter by one or more labels. This field can be either a JSON formatted dictionary of label names and values, where the values are optional and can be set to None (e.g. \`{"label1":"value1", "label2": null}\` ), or a comma-separated list of label names and values (e.g \`label1=value1,label2=\`. If a label name is specified without a value, the filter will match all service connectors that have that label present, regardless of value.'), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The name to filter by'), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'resource_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Filter by the ID of the resource instance that the connector is configured to access'), 'resource_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Filter by the type of resource that the connector can be used to access'), 'scope_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The type to scope this query to.'), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'secret_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, title="Filter by the ID of the secret that contains the service connector's credentials", metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'user_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='User to filter by', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'workspace_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Workspace to filter by', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str | None*

#### page *: int*

#### resource_id *: str | None*

#### resource_type *: str | None*

#### scope_type *: str | None*

#### scope_workspace *: UUID | None*

#### secret_id *: UUID | str | None*

#### size *: int*

#### sort_by *: str*

#### updated *: datetime | str | None*

#### user_id *: UUID | str | None*

#### validate_labels() → [ServiceConnectorFilter](#zenml.models.v2.core.service_connector.ServiceConnectorFilter)

Parse the labels string into a label dictionary and vice-versa.

Returns:
: The validated values.

#### workspace_id *: UUID | str | None*

### *class* zenml.models.v2.core.service_connector.ServiceConnectorRequest(\*, user: ~uuid.UUID, workspace: ~uuid.UUID, name: ~typing.Annotated[str, ~annotated_types.MaxLen(max_length=255)], connector_type: ~typing.Annotated[str | ~zenml.models.v2.misc.service_connector_type.ServiceConnectorTypeModel, \_PydanticGeneralMetadata(union_mode='left_to_right')], description: str = '', auth_method: ~typing.Annotated[str, ~annotated_types.MaxLen(max_length=255)], resource_types: ~typing.List[str] = None, resource_id: ~typing.Annotated[str | None, ~annotated_types.MaxLen(max_length=255)] = None, supports_instances: bool = False, expires_at: ~datetime.datetime | None = None, expires_skew_tolerance: int | None = None, expiration_seconds: int | None = None, configuration: ~typing.Dict[str, ~typing.Any] = None, secrets: ~typing.Dict[str, ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)] | None] = None, labels: ~typing.Dict[str, str] = None)

Bases: [`WorkspaceScopedRequest`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedRequest)

Request model for service connectors.

#### ANALYTICS_FIELDS *: ClassVar[List[str]]* *= ['connector_type', 'auth_method', 'resource_types']*

#### auth_method *: str*

#### configuration *: Dict[str, Any]*

#### connector_type *: str | [ServiceConnectorTypeModel](zenml.models.md#zenml.models.ServiceConnectorTypeModel)*

#### description *: str*

#### *property* emojified_connector_type *: str*

Get the emojified connector type.

Returns:
: The emojified connector type.

#### *property* emojified_resource_types *: List[str]*

Get the emojified connector type.

Returns:
: The emojified connector type.

#### expiration_seconds *: int | None*

#### expires_at *: datetime | None*

#### expires_skew_tolerance *: int | None*

#### get_analytics_metadata() → Dict[str, Any]

Format the resource types in the analytics metadata.

Returns:
: Dict of analytics metadata.

#### labels *: Dict[str, str]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'auth_method': FieldInfo(annotation=str, required=True, title='The authentication method that the connector instance uses to access the resources.', metadata=[MaxLen(max_length=255)]), 'configuration': FieldInfo(annotation=Dict[str, Any], required=False, default_factory=dict, title='The service connector configuration, not including secrets.'), 'connector_type': FieldInfo(annotation=Union[str, ServiceConnectorTypeModel], required=True, title='The type of service connector.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'description': FieldInfo(annotation=str, required=False, default='', title='The service connector instance description.'), 'expiration_seconds': FieldInfo(annotation=Union[int, NoneType], required=False, default=None, title='The duration, in seconds, that the temporary credentials generated by this connector should remain valid. Only applicable for connectors and authentication methods that involve generating temporary credentials from the ones configured in the connector.'), 'expires_at': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None, title='Time when the authentication credentials configured for the connector expire. If omitted, the credentials do not expire.'), 'expires_skew_tolerance': FieldInfo(annotation=Union[int, NoneType], required=False, default=None, title='The number of seconds of tolerance to apply when checking whether the authentication credentials configured for the connector have expired. If omitted, no tolerance is applied.'), 'labels': FieldInfo(annotation=Dict[str, str], required=False, default_factory=dict, title='Service connector labels.'), 'name': FieldInfo(annotation=str, required=True, title='The service connector name.', metadata=[MaxLen(max_length=255)]), 'resource_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Uniquely identifies a specific resource instance that the connector instance can be used to access. If omitted, the connector instance can be used to access any and all resource instances that the authentication method and resource type(s) allow.', metadata=[MaxLen(max_length=255)]), 'resource_types': FieldInfo(annotation=List[str], required=False, default_factory=list, title='The type(s) of resource that the connector instance can be used to gain access to.'), 'secrets': FieldInfo(annotation=Dict[str, Union[Annotated[SecretStr, PlainSerializer], NoneType]], required=False, default_factory=dict, title='The service connector secrets.'), 'supports_instances': FieldInfo(annotation=bool, required=False, default=False, title='Indicates whether the connector instance can be used to access multiple instances of the configured resource type.'), 'user': FieldInfo(annotation=UUID, required=True, title='The id of the user that created this resource.'), 'workspace': FieldInfo(annotation=UUID, required=True, title='The workspace to which this resource belongs.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### resource_id *: str | None*

#### resource_types *: List[str]*

#### secrets *: <lambda>, return_type=PydanticUndefined, when_used=json)] | None]*

#### supports_instances *: bool*

#### *property* type *: str*

Get the connector type.

Returns:
: The connector type.

#### user *: UUID*

#### validate_and_configure_resources(connector_type: [ServiceConnectorTypeModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorTypeModel), resource_types: str | List[str] | None = None, resource_id: str | None = None, configuration: Dict[str, Any] | None = None, secrets: Dict[str, SecretStr | None] | None = None) → None

Validate and configure the resources that the connector can be used to access.

Args:
: connector_type: The connector type specification used to validate
  : the connector configuration.
  <br/>
  resource_types: The type(s) of resource that the connector instance
  : can be used to access. If omitted, a multi-type connector is
    configured.
  <br/>
  resource_id: Uniquely identifies a specific resource instance that
  : the connector instance can be used to access.
  <br/>
  configuration: The connector configuration.
  secrets: The connector secrets.

#### workspace *: UUID*

### *class* zenml.models.v2.core.service_connector.ServiceConnectorResponse(\*, body: [ServiceConnectorResponseBody](#zenml.models.v2.core.service_connector.ServiceConnectorResponseBody) | None = None, metadata: [ServiceConnectorResponseMetadata](#zenml.models.v2.core.service_connector.ServiceConnectorResponseMetadata) | None = None, resources: [ServiceConnectorResponseResources](#zenml.models.v2.core.service_connector.ServiceConnectorResponseResources) | None = None, id: UUID, permission_denied: bool = False, name: Annotated[str, MaxLen(max_length=255)])

Bases: `WorkspaceScopedResponse[ServiceConnectorResponseBody, ServiceConnectorResponseMetadata, ServiceConnectorResponseResources]`

Response model for service connectors.

#### *property* auth_method *: str*

The auth_method property.

Returns:
: the value of the property.

#### body *: 'AnyBody' | None*

#### *property* configuration *: Dict[str, Any]*

The configuration property.

Returns:
: the value of the property.

#### *property* connector_type *: str | [ServiceConnectorTypeModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorTypeModel)*

The connector_type property.

Returns:
: the value of the property.

#### *property* description *: str*

The description property.

Returns:
: the value of the property.

#### *property* emojified_connector_type *: str*

Get the emojified connector type.

Returns:
: The emojified connector type.

#### *property* emojified_resource_types *: List[str]*

Get the emojified connector type.

Returns:
: The emojified connector type.

#### *property* expiration_seconds *: int | None*

The expiration_seconds property.

Returns:
: the value of the property.

#### *property* expires_at *: datetime | None*

The expires_at property.

Returns:
: the value of the property.

#### *property* expires_skew_tolerance *: int | None*

The expires_skew_tolerance property.

Returns:
: the value of the property.

#### *property* full_configuration *: Dict[str, str]*

Get the full connector configuration, including secrets.

Returns:
: The full connector configuration, including secrets.

#### get_analytics_metadata() → Dict[str, Any]

Add the service connector labels to analytics metadata.

Returns:
: Dict of analytics metadata.

#### get_hydrated_version() → [ServiceConnectorResponse](#zenml.models.v2.core.service_connector.ServiceConnectorResponse)

Get the hydrated version of this service connector.

Returns:
: an instance of the same entity with the metadata field attached.

#### id *: UUID*

#### *property* is_multi_instance *: bool*

Checks if the connector is multi-instance.

A multi-instance connector is configured to access multiple instances
of the configured resource type.

Returns:
: True if the connector is multi-instance, False otherwise.

#### *property* is_multi_type *: bool*

Checks if the connector is multi-type.

A multi-type connector can be used to access multiple types of
resources.

Returns:
: True if the connector is multi-type, False otherwise.

#### *property* is_single_instance *: bool*

Checks if the connector is single-instance.

A single-instance connector is configured to access only a single
instance of the configured resource type or does not support multiple
resource instances.

Returns:
: True if the connector is single-instance, False otherwise.

#### *property* labels *: Dict[str, str]*

The labels property.

Returns:
: the value of the property.

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[ServiceConnectorResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[ServiceConnectorResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='The service connector name.', metadata=[MaxLen(max_length=255)]), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[ServiceConnectorResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str*

#### permission_denied *: bool*

#### *property* resource_id *: str | None*

The resource_id property.

Returns:
: the value of the property.

#### *property* resource_types *: List[str]*

The resource_types property.

Returns:
: the value of the property.

#### resources *: 'AnyResources' | None*

#### *property* secret_id *: UUID | None*

The secret_id property.

Returns:
: the value of the property.

#### *property* secrets *: Dict[str, SecretStr | None]*

The secrets property.

Returns:
: the value of the property.

#### set_connector_type(value: str | [ServiceConnectorTypeModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorTypeModel)) → None

Auxiliary method to set the connector type.

Args:
: value: the new value for the connector type.

#### *property* supports_instances *: bool*

The supports_instances property.

Returns:
: the value of the property.

#### *property* type *: str*

Get the connector type.

Returns:
: The connector type.

#### validate_and_configure_resources(connector_type: [ServiceConnectorTypeModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorTypeModel), resource_types: str | List[str] | None = None, resource_id: str | None = None, configuration: Dict[str, Any] | None = None, secrets: Dict[str, SecretStr | None] | None = None) → None

Validate and configure the resources that the connector can be used to access.

Args:
: connector_type: The connector type specification used to validate
  : the connector configuration.
  <br/>
  resource_types: The type(s) of resource that the connector instance
  : can be used to access. If omitted, a multi-type connector is
    configured.
  <br/>
  resource_id: Uniquely identifies a specific resource instance that
  : the connector instance can be used to access.
  <br/>
  configuration: The connector configuration.
  secrets: The connector secrets.

### *class* zenml.models.v2.core.service_connector.ServiceConnectorResponseBody(\*, created: datetime, updated: datetime, user: [UserResponse](#zenml.models.v2.core.user.UserResponse) | None = None, description: str = '', connector_type: Annotated[str | [ServiceConnectorTypeModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorTypeModel), \_PydanticGeneralMetadata(union_mode='left_to_right')], auth_method: Annotated[str, MaxLen(max_length=255)], resource_types: List[str] = None, resource_id: Annotated[str | None, MaxLen(max_length=255)] = None, supports_instances: bool = False, expires_at: datetime | None = None, expires_skew_tolerance: int | None = None)

Bases: [`WorkspaceScopedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseBody)

Response body for service connectors.

#### auth_method *: str*

#### connector_type *: str | [ServiceConnectorTypeModel](zenml.models.md#zenml.models.ServiceConnectorTypeModel)*

#### created *: datetime*

#### description *: str*

#### expires_at *: datetime | None*

#### expires_skew_tolerance *: int | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'auth_method': FieldInfo(annotation=str, required=True, title='The authentication method that the connector instance uses to access the resources.', metadata=[MaxLen(max_length=255)]), 'connector_type': FieldInfo(annotation=Union[str, ServiceConnectorTypeModel], required=True, title='The type of service connector.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'description': FieldInfo(annotation=str, required=False, default='', title='The service connector instance description.'), 'expires_at': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None, title='Time when the authentication credentials configured for the connector expire. If omitted, the credentials do not expire.'), 'expires_skew_tolerance': FieldInfo(annotation=Union[int, NoneType], required=False, default=None, title='The number of seconds of tolerance to apply when checking whether the authentication credentials configured for the connector have expired. If omitted, no tolerance is applied.'), 'resource_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Uniquely identifies a specific resource instance that the connector instance can be used to access. If omitted, the connector instance can be used to access any and all resource instances that the authentication method and resource type(s) allow.', metadata=[MaxLen(max_length=255)]), 'resource_types': FieldInfo(annotation=List[str], required=False, default_factory=list, title='The type(s) of resource that the connector instance can be used to gain access to.'), 'supports_instances': FieldInfo(annotation=bool, required=False, default=False, title='Indicates whether the connector instance can be used to access multiple instances of the configured resource type.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.'), 'user': FieldInfo(annotation=Union[UserResponse, NoneType], required=False, default=None, title='The user who created this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### resource_id *: str | None*

#### resource_types *: List[str]*

#### supports_instances *: bool*

#### updated *: datetime*

#### user *: 'UserResponse' | None*

### *class* zenml.models.v2.core.service_connector.ServiceConnectorResponseMetadata(\*, workspace: ~zenml.models.v2.core.workspace.WorkspaceResponse, configuration: ~typing.Dict[str, ~typing.Any] = None, secret_id: ~uuid.UUID | None = None, expiration_seconds: int | None = None, secrets: ~typing.Dict[str, ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)] | None] = None, labels: ~typing.Dict[str, str] = None)

Bases: [`WorkspaceScopedResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseMetadata)

Response metadata for service connectors.

#### configuration *: Dict[str, Any]*

#### expiration_seconds *: int | None*

#### labels *: Dict[str, str]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'configuration': FieldInfo(annotation=Dict[str, Any], required=False, default_factory=dict, title='The service connector configuration, not including secrets.'), 'expiration_seconds': FieldInfo(annotation=Union[int, NoneType], required=False, default=None, title='The duration, in seconds, that the temporary credentials generated by this connector should remain valid. Only applicable for connectors and authentication methods that involve generating temporary credentials from the ones configured in the connector.'), 'labels': FieldInfo(annotation=Dict[str, str], required=False, default_factory=dict, title='Service connector labels.'), 'secret_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The ID of the secret that contains the service connector secret configuration values.'), 'secrets': FieldInfo(annotation=Dict[str, Union[Annotated[SecretStr, PlainSerializer], NoneType]], required=False, default_factory=dict, title='The service connector secrets.'), 'workspace': FieldInfo(annotation=WorkspaceResponse, required=True, title='The workspace of this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### secret_id *: UUID | None*

#### secrets *: <lambda>, return_type=PydanticUndefined, when_used=json)] | None]*

#### workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

### *class* zenml.models.v2.core.service_connector.ServiceConnectorResponseResources(\*\*extra_data: Any)

Bases: [`WorkspaceScopedResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseResources)

Class for all resource models associated with the service connector entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.service_connector.ServiceConnectorUpdate(\*, name: ~typing.Annotated[str | None, ~annotated_types.MaxLen(max_length=255)] = None, connector_type: ~typing.Annotated[str | ~zenml.models.v2.misc.service_connector_type.ServiceConnectorTypeModel | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, description: str | None = None, auth_method: ~typing.Annotated[str | None, ~annotated_types.MaxLen(max_length=255)] = None, resource_types: ~typing.List[str] | None = None, resource_id: ~typing.Annotated[str | None, ~annotated_types.MaxLen(max_length=255)] = None, supports_instances: bool | None = None, expires_at: ~datetime.datetime | None = None, expires_skew_tolerance: int | None = None, expiration_seconds: int | None = None, configuration: ~typing.Dict[str, ~typing.Any] | None = None, secrets: ~typing.Dict[str, ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)] | None] | None = None, labels: ~typing.Dict[str, str] | None = None)

Bases: [`BaseUpdate`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseUpdate)

Model used for service connector updates.

Most fields in the update model are optional and will not be updated if
omitted. However, the following fields are “special” and leaving them out
will also cause the corresponding value to be removed from the service
connector in the database:

* the resource_id field
* the expiration_seconds field

In addition to the above exceptions, the following rules apply:

* the configuration and secrets fields together represent a full

valid configuration update, not just a partial update. If either is
set (i.e. not None) in the update, their values are merged together and
will replace the existing configuration and secrets values.
\* the secret_id field value in the update is ignored, given that
secrets are managed internally by the ZenML store.
\* the labels field is also a full labels update: if set (i.e. not
None), all existing labels are removed and replaced by the new labels
in the update.

NOTE: the attributes here override the ones in the base class, so they
have a None default value.

#### ANALYTICS_FIELDS *: ClassVar[List[str]]* *= ['connector_type', 'auth_method', 'resource_types']*

#### auth_method *: str | None*

#### configuration *: Dict[str, Any] | None*

#### connector_type *: str | [ServiceConnectorTypeModel](zenml.models.md#zenml.models.ServiceConnectorTypeModel) | None*

#### convert_to_request() → [ServiceConnectorRequest](#zenml.models.v2.core.service_connector.ServiceConnectorRequest)

Method to generate a service connector request object from self.

For certain operations, the service connector update model need to
adhere to the limitations set by the request model. In order to use
update models in such situations, we need to be able to convert an
update model into a request model.

Returns:
: The equivalent request model

Raises:
: RuntimeError: if the model can not be converted to a request model.

#### description *: str | None*

#### expiration_seconds *: int | None*

#### expires_at *: datetime | None*

#### expires_skew_tolerance *: int | None*

#### get_analytics_metadata() → Dict[str, Any]

Format the resource types in the analytics metadata.

Returns:
: Dict of analytics metadata.

#### labels *: Dict[str, str] | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'auth_method': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The authentication method that the connector instance uses to access the resources.', metadata=[MaxLen(max_length=255)]), 'configuration': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, title='The service connector configuration, not including secrets.'), 'connector_type': FieldInfo(annotation=Union[str, ServiceConnectorTypeModel, NoneType], required=False, default=None, title='The type of service connector.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The service connector instance description.'), 'expiration_seconds': FieldInfo(annotation=Union[int, NoneType], required=False, default=None, title='The duration, in seconds, that the temporary credentials generated by this connector should remain valid. Only applicable for connectors and authentication methods that involve generating temporary credentials from the ones configured in the connector.'), 'expires_at': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None, title='Time when the authentication credentials configured for the connector expire. If omitted, the credentials do not expire.'), 'expires_skew_tolerance': FieldInfo(annotation=Union[int, NoneType], required=False, default=None, title='The number of seconds of tolerance to apply when checking whether the authentication credentials configured for the connector have expired. If omitted, no tolerance is applied.'), 'labels': FieldInfo(annotation=Union[Dict[str, str], NoneType], required=False, default=None, title='Service connector labels.'), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The service connector name.', metadata=[MaxLen(max_length=255)]), 'resource_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Uniquely identifies a specific resource instance that the connector instance can be used to access. If omitted, the connector instance can be used to access any and all resource instances that the authentication method and resource type(s) allow.', metadata=[MaxLen(max_length=255)]), 'resource_types': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None, title='The type(s) of resource that the connector instance can be used to gain access to.'), 'secrets': FieldInfo(annotation=Union[Dict[str, Union[Annotated[SecretStr, PlainSerializer], NoneType]], NoneType], required=False, default=None, title='The service connector secrets.'), 'supports_instances': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, title='Indicates whether the connector instance can be used to access multiple instances of the configured resource type.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

#### resource_id *: str | None*

#### resource_types *: List[str] | None*

#### secrets *: <lambda>, return_type=PydanticUndefined, when_used=json)] | None] | None*

#### supports_instances *: bool | None*

#### *property* type *: str | None*

Get the connector type.

Returns:
: The connector type.

#### validate_and_configure_resources(connector_type: [ServiceConnectorTypeModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorTypeModel), resource_types: str | List[str] | None = None, resource_id: str | None = None, configuration: Dict[str, Any] | None = None, secrets: Dict[str, SecretStr | None] | None = None) → None

Validate and configure the resources that the connector can be used to access.

Args:
: connector_type: The connector type specification used to validate
  : the connector configuration.
  <br/>
  resource_types: The type(s) of resource that the connector instance
  : can be used to access. If omitted, a multi-type connector is
    configured.
  <br/>
  resource_id: Uniquely identifies a specific resource instance that
  : the connector instance can be used to access.
  <br/>
  configuration: The connector configuration.
  secrets: The connector secrets.

## zenml.models.v2.core.stack module

Models representing stacks.

### *class* zenml.models.v2.core.stack.StackFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None, name: str | None = None, description: str | None = None, workspace_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, user_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, component_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None)

Bases: [`WorkspaceScopedFilter`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedFilter)

Model to enable advanced filtering of all StackModels.

The Stack Model needs additional scoping. As such the \_scope_user field
can be set to the user that is doing the filtering. The
generate_filter() method of the baseclass is overwritten to include the
scoping.

#### FILTER_EXCLUDE_FIELDS *: ClassVar[List[str]]* *= ['sort_by', 'page', 'size', 'logical_operator', 'scope_workspace', 'component_id']*

#### component_id *: UUID | str | None*

#### created *: datetime | str | None*

#### description *: str | None*

#### get_custom_filters() → List[ColumnElement[bool]]

Get custom filters.

Returns:
: A list of custom filters.

#### id *: UUID | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'component_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Component in the stack', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Description of the stack'), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Name of the stack'), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'user_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='User of the stack', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'workspace_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Workspace of the stack', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str | None*

#### page *: int*

#### scope_workspace *: UUID | None*

#### size *: int*

#### sort_by *: str*

#### updated *: datetime | str | None*

#### user_id *: UUID | str | None*

#### workspace_id *: UUID | str | None*

### *class* zenml.models.v2.core.stack.StackRequest(\*, user: UUID | None = None, workspace: UUID | None = None, name: Annotated[str, MaxLen(max_length=255)], description: Annotated[str, MaxLen(max_length=255)] = '', stack_spec_path: str | None = None, components: Dict[[StackComponentType](zenml.md#zenml.enums.StackComponentType), List[UUID | [ComponentInfo](zenml.models.v2.misc.md#zenml.models.v2.misc.info_models.ComponentInfo)]], labels: Dict[str, Any] | None = None, service_connectors: List[UUID | [ServiceConnectorInfo](zenml.models.v2.misc.md#zenml.models.v2.misc.info_models.ServiceConnectorInfo)] = [])

Bases: [`BaseRequest`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseRequest)

Request model for a stack.

#### components *: Dict[[StackComponentType](zenml.md#zenml.enums.StackComponentType), List[UUID | [ComponentInfo](zenml.models.v2.misc.md#zenml.models.v2.misc.info_models.ComponentInfo)]]*

#### description *: str*

#### *property* is_valid *: bool*

Check if the stack is valid.

Returns:
: True if the stack is valid, False otherwise.

#### labels *: Dict[str, Any] | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'components': FieldInfo(annotation=Dict[StackComponentType, List[Union[UUID, ComponentInfo]]], required=True, title='The mapping for the components of the full stack registration.', description='The mapping from component types to either UUIDs of existing components or request information for brand new components.'), 'description': FieldInfo(annotation=str, required=False, default='', title='The description of the stack', metadata=[MaxLen(max_length=255)]), 'labels': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, title='The stack labels.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the stack.', metadata=[MaxLen(max_length=255)]), 'service_connectors': FieldInfo(annotation=List[Union[UUID, ServiceConnectorInfo]], required=False, default=[], title='The service connectors dictionary for the full stack registration.', description='The UUID of an already existing service connector or request information to create a service connector from scratch.'), 'stack_spec_path': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The path to the stack spec used for mlstacks deployments.'), 'user': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### service_connectors *: List[UUID | [ServiceConnectorInfo](zenml.models.v2.misc.md#zenml.models.v2.misc.info_models.ServiceConnectorInfo)]*

#### stack_spec_path *: str | None*

#### user *: UUID | None*

#### workspace *: UUID | None*

### *class* zenml.models.v2.core.stack.StackResponse(\*, body: [StackResponseBody](#zenml.models.v2.core.stack.StackResponseBody) | None = None, metadata: [StackResponseMetadata](#zenml.models.v2.core.stack.StackResponseMetadata) | None = None, resources: [StackResponseResources](#zenml.models.v2.core.stack.StackResponseResources) | None = None, id: UUID, permission_denied: bool = False, name: Annotated[str, MaxLen(max_length=255)])

Bases: `WorkspaceScopedResponse[StackResponseBody, StackResponseMetadata, StackResponseResources]`

Response model for stacks.

#### body *: 'AnyBody' | None*

#### *property* components *: Dict[[StackComponentType](zenml.md#zenml.enums.StackComponentType), List[[ComponentResponse](zenml.models.md#zenml.models.ComponentResponse)]]*

The components property.

Returns:
: the value of the property.

#### *property* description *: str | None*

The description property.

Returns:
: the value of the property.

#### get_analytics_metadata() → Dict[str, Any]

Add the stack components to the stack analytics metadata.

Returns:
: Dict of analytics metadata.

#### get_hydrated_version() → [StackResponse](#zenml.models.v2.core.stack.StackResponse)

Get the hydrated version of this stack.

Returns:
: an instance of the same entity with the metadata field attached.

#### id *: UUID*

#### *property* is_valid *: bool*

Check if the stack is valid.

Returns:
: True if the stack is valid, False otherwise.

#### *property* labels *: Dict[str, Any] | None*

The labels property.

Returns:
: the value of the property.

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[StackResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[StackResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the stack.', metadata=[MaxLen(max_length=255)]), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[StackResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str*

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* stack_spec_path *: str | None*

The stack_spec_path property.

Returns:
: the value of the property.

#### to_yaml() → Dict[str, Any]

Create yaml representation of the Stack Model.

Returns:
: The yaml representation of the Stack Model.

### *class* zenml.models.v2.core.stack.StackResponseBody(\*, created: datetime, updated: datetime, user: [UserResponse](#zenml.models.v2.core.user.UserResponse) | None = None)

Bases: [`WorkspaceScopedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseBody)

Response body for stacks.

#### created *: datetime*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.'), 'user': FieldInfo(annotation=Union[UserResponse, NoneType], required=False, default=None, title='The user who created this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### updated *: datetime*

#### user *: [UserResponse](zenml.models.md#zenml.models.UserResponse) | None*

### *class* zenml.models.v2.core.stack.StackResponseMetadata(\*, workspace: [WorkspaceResponse](#zenml.models.v2.core.workspace.WorkspaceResponse), components: Dict[[StackComponentType](zenml.md#zenml.enums.StackComponentType), List[[ComponentResponse](#zenml.models.v2.core.component.ComponentResponse)]], description: Annotated[str | None, MaxLen(max_length=255)] = '', stack_spec_path: str | None = None, labels: Dict[str, Any] | None = None)

Bases: [`WorkspaceScopedResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseMetadata)

Response metadata for stacks.

#### components *: Dict[[StackComponentType](zenml.md#zenml.enums.StackComponentType), List[[ComponentResponse](zenml.models.md#zenml.models.ComponentResponse)]]*

#### description *: str | None*

#### labels *: Dict[str, Any] | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'components': FieldInfo(annotation=Dict[StackComponentType, List[ComponentResponse]], required=True, title='A mapping of stack component types to the actualinstances of components of this type.'), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default='', title='The description of the stack', metadata=[MaxLen(max_length=255)]), 'labels': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, title='The stack labels.'), 'stack_spec_path': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The path to the stack spec used for mlstacks deployments.'), 'workspace': FieldInfo(annotation=WorkspaceResponse, required=True, title='The workspace of this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### stack_spec_path *: str | None*

#### workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

### *class* zenml.models.v2.core.stack.StackResponseResources(\*\*extra_data: Any)

Bases: [`WorkspaceScopedResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseResources)

Class for all resource models associated with the stack entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.stack.StackUpdate(\*, name: Annotated[str | None, MaxLen(max_length=255)] = None, description: Annotated[str | None, MaxLen(max_length=255)] = None, stack_spec_path: str | None = None, components: Dict[[StackComponentType](zenml.md#zenml.enums.StackComponentType), List[UUID]] | None = None, labels: Dict[str, Any] | None = None)

Bases: [`BaseUpdate`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseUpdate)

Update model for stacks.

#### components *: Dict[[StackComponentType](zenml.md#zenml.enums.StackComponentType), List[UUID]] | None*

#### description *: str | None*

#### labels *: Dict[str, Any] | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'components': FieldInfo(annotation=Union[Dict[StackComponentType, List[UUID]], NoneType], required=False, default=None, title='A mapping of stack component types to the actualinstances of components of this type.'), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The description of the stack', metadata=[MaxLen(max_length=255)]), 'labels': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, title='The stack labels.'), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The name of the stack.', metadata=[MaxLen(max_length=255)]), 'stack_spec_path': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The path to the stack spec used for mlstacks deployments.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

#### stack_spec_path *: str | None*

## zenml.models.v2.core.step_run module

Models representing steps runs.

### *class* zenml.models.v2.core.step_run.StepRunFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None, name: str | None = None, code_hash: str | None = None, cache_key: str | None = None, status: str | None = None, start_time: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, end_time: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, pipeline_run_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, original_step_run_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, user_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, workspace_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None)

Bases: [`WorkspaceScopedFilter`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedFilter)

Model to enable advanced filtering of step runs.

#### cache_key *: str | None*

#### code_hash *: str | None*

#### created *: datetime | str | None*

#### end_time *: datetime | str | None*

#### id *: UUID | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'cache_key': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Cache key for this step run'), 'code_hash': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Code hash for this step run'), 'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'end_time': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='End time for this run', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Name of the step run'), 'original_step_run_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Original id for this step run', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'pipeline_run_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Pipeline run of this step run', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'start_time': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Start time for this run', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'status': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Status of the Step Run'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'user_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='User that produced this step run', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'workspace_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Workspace of this step run', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str | None*

#### original_step_run_id *: UUID | str | None*

#### page *: int*

#### pipeline_run_id *: UUID | str | None*

#### scope_workspace *: UUID | None*

#### size *: int*

#### sort_by *: str*

#### start_time *: datetime | str | None*

#### status *: str | None*

#### updated *: datetime | str | None*

#### user_id *: UUID | str | None*

#### workspace_id *: UUID | str | None*

### *class* zenml.models.v2.core.step_run.StepRunRequest(\*, user: UUID, workspace: UUID, name: Annotated[str, MaxLen(max_length=255)], start_time: datetime | None = None, end_time: datetime | None = None, status: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus), cache_key: Annotated[str | None, MaxLen(max_length=255)] = None, code_hash: Annotated[str | None, MaxLen(max_length=255)] = None, docstring: Annotated[str | None, MaxLen(max_length=65535)] = None, source_code: Annotated[str | None, MaxLen(max_length=65535)] = None, pipeline_run_id: UUID, original_step_run_id: UUID | None = None, parent_step_ids: List[UUID] = None, inputs: Dict[str, UUID] = {}, outputs: Dict[str, UUID] = {}, logs: [LogsRequest](#zenml.models.v2.core.logs.LogsRequest) | None = None, deployment: UUID, model_version_id: UUID | None = None)

Bases: [`WorkspaceScopedRequest`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedRequest)

Request model for step runs.

#### cache_key *: str | None*

#### code_hash *: str | None*

#### deployment *: UUID*

#### docstring *: str | None*

#### end_time *: datetime | None*

#### inputs *: Dict[str, UUID]*

#### logs *: [LogsRequest](zenml.models.md#zenml.models.LogsRequest) | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'cache_key': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The cache key of the step run.', metadata=[MaxLen(max_length=255)]), 'code_hash': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The code hash of the step run.', metadata=[MaxLen(max_length=255)]), 'deployment': FieldInfo(annotation=UUID, required=True, title='The deployment associated with the step run.'), 'docstring': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The docstring of the step function or class.', metadata=[MaxLen(max_length=65535)]), 'end_time': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None, title='The end time of the step run.'), 'inputs': FieldInfo(annotation=Dict[str, UUID], required=False, default={}, title='The IDs of the input artifact versions of the step run.'), 'logs': FieldInfo(annotation=Union[LogsRequest, NoneType], required=False, default=None, title='Logs associated with this step run.'), 'model_version_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The ID of the model version that was configured by this step run explicitly.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the pipeline run step.', metadata=[MaxLen(max_length=255)]), 'original_step_run_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The ID of the original step run if this step was cached.'), 'outputs': FieldInfo(annotation=Dict[str, UUID], required=False, default={}, title='The IDs of the output artifact versions of the step run.'), 'parent_step_ids': FieldInfo(annotation=List[UUID], required=False, default_factory=list, title='The IDs of the parent steps of this step run.'), 'pipeline_run_id': FieldInfo(annotation=UUID, required=True, title='The ID of the pipeline run that this step run belongs to.'), 'source_code': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The source code of the step function or class.', metadata=[MaxLen(max_length=65535)]), 'start_time': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None, title='The start time of the step run.'), 'status': FieldInfo(annotation=ExecutionStatus, required=True, title='The status of the step.'), 'user': FieldInfo(annotation=UUID, required=True, title='The id of the user that created this resource.'), 'workspace': FieldInfo(annotation=UUID, required=True, title='The workspace to which this resource belongs.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_version_id *: UUID | None*

#### name *: str*

#### original_step_run_id *: UUID | None*

#### outputs *: Dict[str, UUID]*

#### parent_step_ids *: List[UUID]*

#### pipeline_run_id *: UUID*

#### source_code *: str | None*

#### start_time *: datetime | None*

#### status *: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus)*

#### user *: UUID*

#### workspace *: UUID*

### *class* zenml.models.v2.core.step_run.StepRunResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `WorkspaceScopedResponse[StepRunResponseBody, StepRunResponseMetadata, StepRunResponseResources]`

Response model for step runs.

#### body *: 'AnyBody' | None*

#### *property* cache_key *: str | None*

The cache_key property.

Returns:
: the value of the property.

#### *property* code_hash *: str | None*

The code_hash property.

Returns:
: the value of the property.

#### *property* config *: [StepConfiguration](zenml.config.md#zenml.config.step_configurations.StepConfiguration)*

The config property.

Returns:
: the value of the property.

#### *property* deployment_id *: UUID*

The deployment_id property.

Returns:
: the value of the property.

#### *property* docstring *: str | None*

The docstring property.

Returns:
: the value of the property.

#### *property* end_time *: datetime | None*

The end_time property.

Returns:
: the value of the property.

#### get_hydrated_version() → [StepRunResponse](#zenml.models.v2.core.step_run.StepRunResponse)

Get the hydrated version of this step run.

Returns:
: an instance of the same entity with the metadata field attached.

#### id *: UUID*

#### *property* input *: [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse)*

Returns the input artifact that was used to run this step.

Returns:
: The input artifact.

Raises:
: ValueError: If there were zero or multiple inputs to this step.

#### *property* inputs *: Dict[str, [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse)]*

The inputs property.

Returns:
: the value of the property.

#### *property* logs *: [LogsResponse](zenml.models.md#zenml.models.LogsResponse) | None*

The logs property.

Returns:
: the value of the property.

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[StepRunResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[StepRunResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the pipeline run step.', metadata=[MaxLen(max_length=255)]), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[StepRunResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### *property* model_version *: [ModelVersionResponse](#zenml.models.v2.core.model_version.ModelVersionResponse) | None*

The model_version property.

Returns:
: the value of the property.

#### *property* model_version_id *: UUID | None*

The model_version_id property.

Returns:
: the value of the property.

#### name *: str*

#### *property* original_step_run_id *: UUID | None*

The original_step_run_id property.

Returns:
: the value of the property.

#### *property* output *: [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse)*

Returns the output artifact that was written by this step.

Returns:
: The output artifact.

Raises:
: ValueError: If there were zero or multiple step outputs.

#### *property* outputs *: Dict[str, [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse)]*

The outputs property.

Returns:
: the value of the property.

#### *property* parent_step_ids *: List[UUID]*

The parent_step_ids property.

Returns:
: the value of the property.

#### permission_denied *: bool*

#### *property* pipeline_run_id *: UUID*

The pipeline_run_id property.

Returns:
: the value of the property.

#### resources *: 'AnyResources' | None*

#### *property* run_metadata *: Dict[str, [RunMetadataResponse](zenml.models.md#zenml.models.RunMetadataResponse)]*

The run_metadata property.

Returns:
: the value of the property.

#### *property* source_code *: str | None*

The source_code property.

Returns:
: the value of the property.

#### *property* spec *: [StepSpec](zenml.config.md#zenml.config.step_configurations.StepSpec)*

The spec property.

Returns:
: the value of the property.

#### *property* start_time *: datetime | None*

The start_time property.

Returns:
: the value of the property.

#### *property* status *: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus)*

The status property.

Returns:
: the value of the property.

### *class* zenml.models.v2.core.step_run.StepRunResponseBody(\*, created: datetime, updated: datetime, user: [UserResponse](#zenml.models.v2.core.user.UserResponse) | None = None, status: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus), inputs: Dict[str, [ArtifactVersionResponse](#zenml.models.v2.core.artifact_version.ArtifactVersionResponse)] = {}, outputs: Dict[str, [ArtifactVersionResponse](#zenml.models.v2.core.artifact_version.ArtifactVersionResponse)] = {}, model_version_id: UUID | None = None)

Bases: [`WorkspaceScopedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseBody)

Response body for step runs.

#### created *: datetime*

#### inputs *: Dict[str, [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'inputs': FieldInfo(annotation=Dict[str, ArtifactVersionResponse], required=False, default={}, title='The input artifact versions of the step run.'), 'model_version_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The ID of the model version that was configured by this step run explicitly.'), 'outputs': FieldInfo(annotation=Dict[str, ArtifactVersionResponse], required=False, default={}, title='The output artifact versions of the step run.'), 'status': FieldInfo(annotation=ExecutionStatus, required=True, title='The status of the step.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.'), 'user': FieldInfo(annotation=Union[UserResponse, NoneType], required=False, default=None, title='The user who created this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_version_id *: UUID | None*

#### outputs *: Dict[str, [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse)]*

#### status *: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus)*

#### updated *: datetime*

#### user *: 'UserResponse' | None*

### *class* zenml.models.v2.core.step_run.StepRunResponseMetadata(\*, workspace: [WorkspaceResponse](#zenml.models.v2.core.workspace.WorkspaceResponse), config: [StepConfiguration](zenml.config.md#zenml.config.step_configurations.StepConfiguration), spec: [StepSpec](zenml.config.md#zenml.config.step_configurations.StepSpec), cache_key: Annotated[str | None, MaxLen(max_length=255)] = None, code_hash: Annotated[str | None, MaxLen(max_length=255)] = None, docstring: Annotated[str | None, MaxLen(max_length=65535)] = None, source_code: Annotated[str | None, MaxLen(max_length=65535)] = None, start_time: datetime | None = None, end_time: datetime | None = None, logs: [LogsResponse](#zenml.models.v2.core.logs.LogsResponse) | None = None, deployment_id: UUID, pipeline_run_id: UUID, original_step_run_id: UUID | None = None, parent_step_ids: List[UUID] = None, run_metadata: Dict[str, [RunMetadataResponse](#zenml.models.v2.core.run_metadata.RunMetadataResponse)] = {})

Bases: [`WorkspaceScopedResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseMetadata)

Response metadata for step runs.

#### cache_key *: str | None*

#### code_hash *: str | None*

#### config *: [StepConfiguration](zenml.config.md#zenml.config.step_configurations.StepConfiguration)*

#### deployment_id *: UUID*

#### docstring *: str | None*

#### end_time *: datetime | None*

#### logs *: [LogsResponse](zenml.models.md#zenml.models.LogsResponse) | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'cache_key': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The cache key of the step run.', metadata=[MaxLen(max_length=255)]), 'code_hash': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The code hash of the step run.', metadata=[MaxLen(max_length=255)]), 'config': FieldInfo(annotation=StepConfiguration, required=True, title='The configuration of the step.'), 'deployment_id': FieldInfo(annotation=UUID, required=True, title='The deployment associated with the step run.'), 'docstring': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The docstring of the step function or class.', metadata=[MaxLen(max_length=65535)]), 'end_time': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None, title='The end time of the step run.'), 'logs': FieldInfo(annotation=Union[LogsResponse, NoneType], required=False, default=None, title='Logs associated with this step run.'), 'original_step_run_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The ID of the original step run if this step was cached.'), 'parent_step_ids': FieldInfo(annotation=List[UUID], required=False, default_factory=list, title='The IDs of the parent steps of this step run.'), 'pipeline_run_id': FieldInfo(annotation=UUID, required=True, title='The ID of the pipeline run that this step run belongs to.'), 'run_metadata': FieldInfo(annotation=Dict[str, RunMetadataResponse], required=False, default={}, title='Metadata associated with this step run.'), 'source_code': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The source code of the step function or class.', metadata=[MaxLen(max_length=65535)]), 'spec': FieldInfo(annotation=StepSpec, required=True, title='The spec of the step.'), 'start_time': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None, title='The start time of the step run.'), 'workspace': FieldInfo(annotation=WorkspaceResponse, required=True, title='The workspace of this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### original_step_run_id *: UUID | None*

#### parent_step_ids *: List[UUID]*

#### pipeline_run_id *: UUID*

#### run_metadata *: Dict[str, [RunMetadataResponse](zenml.models.md#zenml.models.RunMetadataResponse)]*

#### source_code *: str | None*

#### spec *: [StepSpec](zenml.config.md#zenml.config.step_configurations.StepSpec)*

#### start_time *: datetime | None*

#### workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

### *class* zenml.models.v2.core.step_run.StepRunResponseResources(\*\*extra_data: Any)

Bases: [`WorkspaceScopedResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseResources)

Class for all resource models associated with the step run entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow', 'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'model_version': FieldInfo(annotation=Union[ModelVersionResponse, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_version *: [ModelVersionResponse](#zenml.models.v2.core.model_version.ModelVersionResponse) | None*

### *class* zenml.models.v2.core.step_run.StepRunUpdate(\*, outputs: Dict[str, UUID] = {}, saved_artifact_versions: Dict[str, UUID] = {}, loaded_artifact_versions: Dict[str, UUID] = {}, status: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus) | None = None, end_time: datetime | None = None, model_version_id: UUID | None = None)

Bases: `BaseModel`

Update model for step runs.

#### end_time *: datetime | None*

#### loaded_artifact_versions *: Dict[str, UUID]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'end_time': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None, title='The end time of the step run.'), 'loaded_artifact_versions': FieldInfo(annotation=Dict[str, UUID], required=False, default={}, title='The IDs of artifact versions that were loaded by this step run.'), 'model_version_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The ID of the model version that was configured by this step run explicitly.'), 'outputs': FieldInfo(annotation=Dict[str, UUID], required=False, default={}, title='The IDs of the output artifact versions of the step run.'), 'saved_artifact_versions': FieldInfo(annotation=Dict[str, UUID], required=False, default={}, title='The IDs of artifact versions that were saved by this step run.'), 'status': FieldInfo(annotation=Union[ExecutionStatus, NoneType], required=False, default=None, title='The status of the step.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_version_id *: UUID | None*

#### outputs *: Dict[str, UUID]*

#### saved_artifact_versions *: Dict[str, UUID]*

#### status *: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus) | None*

## zenml.models.v2.core.tag module

Models representing tags.

### *class* zenml.models.v2.core.tag.TagFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, name: str | None = None, color: [ColorVariants](zenml.md#zenml.enums.ColorVariants) | None = None)

Bases: [`BaseFilter`](zenml.models.v2.base.md#zenml.models.v2.base.filter.BaseFilter)

Model to enable advanced filtering of all tags.

#### color *: [ColorVariants](zenml.md#zenml.enums.ColorVariants) | None*

#### created *: datetime | str | None*

#### id *: UUID | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'color': FieldInfo(annotation=Union[ColorVariants, NoneType], required=False, default=None, description='The color variant assigned to the tag.'), 'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='The unique title of the tag.'), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str | None*

#### page *: int*

#### size *: int*

#### sort_by *: str*

#### updated *: datetime | str | None*

### *class* zenml.models.v2.core.tag.TagRequest(\*, name: Annotated[str, MaxLen(max_length=255)], color: [ColorVariants](zenml.md#zenml.enums.ColorVariants) = None)

Bases: [`BaseRequest`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseRequest)

Request model for tags.

#### color *: [ColorVariants](zenml.md#zenml.enums.ColorVariants)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'color': FieldInfo(annotation=ColorVariants, required=False, default_factory=<lambda>, description='The color variant assigned to the tag.'), 'name': FieldInfo(annotation=str, required=True, description='The unique title of the tag.', metadata=[MaxLen(max_length=255)])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

### *class* zenml.models.v2.core.tag.TagResponse(\*, body: [TagResponseBody](#zenml.models.v2.core.tag.TagResponseBody) | None = None, metadata: [BaseResponseMetadata](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseMetadata) | None = None, resources: [TagResponseResources](#zenml.models.v2.core.tag.TagResponseResources) | None = None, id: UUID, permission_denied: bool = False, name: Annotated[str, MaxLen(max_length=255)])

Bases: `BaseIdentifiedResponse[TagResponseBody, BaseResponseMetadata, TagResponseResources]`

Response model for tags.

#### body *: 'AnyBody' | None*

#### *property* color *: [ColorVariants](zenml.md#zenml.enums.ColorVariants)*

The color property.

Returns:
: the value of the property.

#### get_hydrated_version() → [TagResponse](#zenml.models.v2.core.tag.TagResponse)

Get the hydrated version of this tag.

Returns:
: an instance of the same entity with the metadata field attached.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[TagResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[BaseResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, description='The unique title of the tag.', metadata=[MaxLen(max_length=255)]), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[TagResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str*

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* tagged_count *: int*

The tagged_count property.

Returns:
: the value of the property.

### *class* zenml.models.v2.core.tag.TagResponseBody(\*, created: datetime, updated: datetime, color: [ColorVariants](zenml.md#zenml.enums.ColorVariants) = None, tagged_count: int)

Bases: [`BaseDatedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseDatedResponseBody)

Response body for tags.

#### color *: [ColorVariants](zenml.md#zenml.enums.ColorVariants)*

#### created *: datetime*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'color': FieldInfo(annotation=ColorVariants, required=False, default_factory=<lambda>, description='The color variant assigned to the tag.'), 'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'tagged_count': FieldInfo(annotation=int, required=True, description='The count of resources tagged with this tag.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### tagged_count *: int*

#### updated *: datetime*

### *class* zenml.models.v2.core.tag.TagResponseResources(\*\*extra_data: Any)

Bases: [`BaseResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseResources)

Class for all resource models associated with the tag entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.tag.TagUpdate(\*, name: str | None = None, color: [ColorVariants](zenml.md#zenml.enums.ColorVariants) | None = None)

Bases: `BaseModel`

Update model for tags.

#### color *: [ColorVariants](zenml.md#zenml.enums.ColorVariants) | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'color': FieldInfo(annotation=Union[ColorVariants, NoneType], required=False, default=None), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

## zenml.models.v2.core.tag_resource module

Models representing the link between tags and resources.

### *class* zenml.models.v2.core.tag_resource.TagResourceRequest(\*, tag_id: UUID, resource_id: UUID, resource_type: [TaggableResourceTypes](zenml.md#zenml.enums.TaggableResourceTypes))

Bases: [`BaseRequest`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseRequest)

Request model for links between tags and resources.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'resource_id': FieldInfo(annotation=UUID, required=True), 'resource_type': FieldInfo(annotation=TaggableResourceTypes, required=True), 'tag_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### resource_id *: UUID*

#### resource_type *: [TaggableResourceTypes](zenml.md#zenml.enums.TaggableResourceTypes)*

#### tag_id *: UUID*

### *class* zenml.models.v2.core.tag_resource.TagResourceResponse(\*, body: [TagResourceResponseBody](#zenml.models.v2.core.tag_resource.TagResourceResponseBody) | None = None, metadata: [BaseResponseMetadata](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseMetadata) | None = None, resources: [TagResourceResponseResources](#zenml.models.v2.core.tag_resource.TagResourceResponseResources) | None = None, id: UUID, permission_denied: bool = False)

Bases: `BaseIdentifiedResponse[TagResourceResponseBody, BaseResponseMetadata, TagResourceResponseResources]`

Response model for the links between tags and resources.

#### body *: 'AnyBody' | None*

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[TagResourceResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[BaseResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[TagResourceResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### *property* resource_id *: UUID*

The resource_id property.

Returns:
: the value of the property.

#### *property* resource_type *: [TaggableResourceTypes](zenml.md#zenml.enums.TaggableResourceTypes)*

The resource_type property.

Returns:
: the value of the property.

#### resources *: 'AnyResources' | None*

#### *property* tag_id *: UUID*

The tag_id property.

Returns:
: the value of the property.

### *class* zenml.models.v2.core.tag_resource.TagResourceResponseBody(\*, created: datetime, updated: datetime, tag_id: UUID, resource_id: UUID, resource_type: [TaggableResourceTypes](zenml.md#zenml.enums.TaggableResourceTypes))

Bases: [`BaseDatedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseDatedResponseBody)

Response body for the links between tags and resources.

#### created *: datetime*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'resource_id': FieldInfo(annotation=UUID, required=True), 'resource_type': FieldInfo(annotation=TaggableResourceTypes, required=True), 'tag_id': FieldInfo(annotation=UUID, required=True), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### resource_id *: UUID*

#### resource_type *: [TaggableResourceTypes](zenml.md#zenml.enums.TaggableResourceTypes)*

#### tag_id *: UUID*

#### updated *: datetime*

### *class* zenml.models.v2.core.tag_resource.TagResourceResponseResources(\*\*extra_data: Any)

Bases: [`BaseResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseResources)

Class for all resource models associated with the tag resource entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## zenml.models.v2.core.trigger module

Collection of all models concerning triggers.

### *class* zenml.models.v2.core.trigger.TriggerFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None, name: str | None = None, event_source_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, action_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, is_active: bool | None = None, action_flavor: str | None = None, action_subtype: str | None = None, event_source_flavor: str | None = None, event_source_subtype: str | None = None)

Bases: [`WorkspaceScopedFilter`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedFilter)

Model to enable advanced filtering of all triggers.

#### FILTER_EXCLUDE_FIELDS *: ClassVar[List[str]]* *= ['sort_by', 'page', 'size', 'logical_operator', 'scope_workspace', 'action_flavor', 'action_subtype', 'event_source_flavor', 'event_source_subtype']*

#### action_flavor *: str | None*

#### action_id *: UUID | str | None*

#### action_subtype *: str | None*

#### created *: datetime | str | None*

#### event_source_flavor *: str | None*

#### event_source_id *: UUID | str | None*

#### event_source_subtype *: str | None*

#### get_custom_filters() → List[ColumnElement[bool]]

Get custom filters.

Returns:
: A list of custom filters.

#### id *: UUID | str | None*

#### is_active *: bool | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'action_flavor': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The flavor of the action that is executed by this trigger.'), 'action_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='The action this trigger is attached to.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'action_subtype': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The subtype of the action that is executed by this trigger.'), 'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'event_source_flavor': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The flavor of the event source that activates this trigger.'), 'event_source_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='The event source this trigger is attached to.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'event_source_subtype': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The subtype of the event source that activates this trigger.'), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'is_active': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, description='Whether the trigger is active.'), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Name of the trigger.'), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str | None*

#### page *: int*

#### scope_workspace *: UUID | None*

#### size *: int*

#### sort_by *: str*

#### updated *: datetime | str | None*

### *class* zenml.models.v2.core.trigger.TriggerRequest(\*, user: UUID, workspace: UUID, name: Annotated[str, MaxLen(max_length=255)], description: Annotated[str, MaxLen(max_length=255)] = '', action_id: UUID, schedule: [Schedule](zenml.config.md#zenml.config.schedule.Schedule) | None = None, event_source_id: UUID | None = None, event_filter: Dict[str, Any] | None = None)

Bases: [`WorkspaceScopedRequest`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedRequest)

Model for creating a new trigger.

#### action_id *: UUID*

#### description *: str*

#### event_filter *: Dict[str, Any] | None*

#### event_source_id *: UUID | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'action_id': FieldInfo(annotation=UUID, required=True, title='The action that is executed by this trigger.'), 'description': FieldInfo(annotation=str, required=False, default='', title='The description of the trigger', metadata=[MaxLen(max_length=255)]), 'event_filter': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, title='Filter applied to events that activate this trigger. Only set if the trigger is activated by an event source.'), 'event_source_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The event source that activates this trigger. Either a schedule or an event source is required.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the trigger.', metadata=[MaxLen(max_length=255)]), 'schedule': FieldInfo(annotation=Union[Schedule, NoneType], required=False, default=None, title='The schedule for the trigger. Either a schedule or an event source is required.'), 'user': FieldInfo(annotation=UUID, required=True, title='The id of the user that created this resource.'), 'workspace': FieldInfo(annotation=UUID, required=True, title='The workspace to which this resource belongs.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### schedule *: [Schedule](zenml.config.md#zenml.config.schedule.Schedule) | None*

#### user *: UUID*

#### workspace *: UUID*

### *class* zenml.models.v2.core.trigger.TriggerResponse(\*, body: [TriggerResponseBody](#zenml.models.v2.core.trigger.TriggerResponseBody) | None = None, metadata: [TriggerResponseMetadata](#zenml.models.v2.core.trigger.TriggerResponseMetadata) | None = None, resources: [TriggerResponseResources](#zenml.models.v2.core.trigger.TriggerResponseResources) | None = None, id: UUID, permission_denied: bool = False, name: Annotated[str, MaxLen(max_length=255)])

Bases: `WorkspaceScopedResponse[TriggerResponseBody, TriggerResponseMetadata, TriggerResponseResources]`

Response model for models.

#### *property* action *: [ActionResponse](zenml.models.md#zenml.models.ActionResponse)*

The action property.

Returns:
: the value of the property.

#### *property* action_flavor *: str*

The action_flavor property.

Returns:
: the value of the property.

#### *property* action_subtype *: str*

The action_subtype property.

Returns:
: the value of the property.

#### body *: 'AnyBody' | None*

#### *property* description *: str*

The description property.

Returns:
: the value of the property.

#### *property* event_filter *: Dict[str, Any] | None*

The event_filter property.

Returns:
: the value of the property.

#### *property* event_source *: [EventSourceResponse](zenml.models.md#zenml.models.EventSourceResponse) | None*

The event_source property.

Returns:
: the value of the property.

#### *property* event_source_flavor *: str | None*

The event_source_flavor property.

Returns:
: the value of the property.

#### *property* event_source_subtype *: str | None*

The event_source_subtype property.

Returns:
: the value of the property.

#### *property* executions *: [Page](zenml.models.v2.base.md#id327)[[TriggerExecutionResponse](zenml.models.md#zenml.models.TriggerExecutionResponse)]*

The event_source property.

Returns:
: the value of the property.

#### get_hydrated_version() → [TriggerResponse](#zenml.models.v2.core.trigger.TriggerResponse)

Get the hydrated version of this trigger.

Returns:
: An instance of the same entity with the metadata field attached.

#### id *: UUID*

#### *property* is_active *: bool*

The is_active property.

Returns:
: the value of the property.

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[TriggerResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[TriggerResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='The name of the trigger', metadata=[MaxLen(max_length=255)]), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[TriggerResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str*

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

### *class* zenml.models.v2.core.trigger.TriggerResponseBody(\*, created: datetime, updated: datetime, user: [UserResponse](#zenml.models.v2.core.user.UserResponse) | None = None, action_flavor: Annotated[str, MaxLen(max_length=255)], action_subtype: str, event_source_flavor: Annotated[str | None, MaxLen(max_length=255)] = None, event_source_subtype: Annotated[str | None, MaxLen(max_length=255)] = None, is_active: bool)

Bases: [`WorkspaceScopedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseBody)

Response body for triggers.

#### action_flavor *: str*

#### action_subtype *: str*

#### created *: datetime*

#### event_source_flavor *: str | None*

#### event_source_subtype *: str | None*

#### is_active *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'action_flavor': FieldInfo(annotation=str, required=True, title='The flavor of the action that is executed by this trigger.', metadata=[MaxLen(max_length=255)]), 'action_subtype': FieldInfo(annotation=str, required=True, title='The subtype of the action that is executed by this trigger.'), 'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'event_source_flavor': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The flavor of the event source that activates this trigger. Not set if the trigger is activated by a schedule.', metadata=[MaxLen(max_length=255)]), 'event_source_subtype': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The subtype of the event source that activates this trigger. Not set if the trigger is activated by a schedule.', metadata=[MaxLen(max_length=255)]), 'is_active': FieldInfo(annotation=bool, required=True, title='Whether the trigger is active.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.'), 'user': FieldInfo(annotation=Union[UserResponse, NoneType], required=False, default=None, title='The user who created this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### updated *: datetime*

#### user *: 'UserResponse' | None*

### *class* zenml.models.v2.core.trigger.TriggerResponseMetadata(\*, workspace: [WorkspaceResponse](#zenml.models.v2.core.workspace.WorkspaceResponse), description: Annotated[str, MaxLen(max_length=255)] = '', event_filter: Dict[str, Any] | None = None, schedule: [Schedule](zenml.config.md#zenml.config.schedule.Schedule) | None = None)

Bases: [`WorkspaceScopedResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseMetadata)

Response metadata for triggers.

#### description *: str*

#### event_filter *: Dict[str, Any] | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'description': FieldInfo(annotation=str, required=False, default='', title='The description of the trigger.', metadata=[MaxLen(max_length=255)]), 'event_filter': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, title='The event that activates this trigger. Not set if the trigger is activated by a schedule.'), 'schedule': FieldInfo(annotation=Union[Schedule, NoneType], required=False, default=None, title='The schedule that activates this trigger. Not set if the trigger is activated by an event source.'), 'workspace': FieldInfo(annotation=WorkspaceResponse, required=True, title='The workspace of this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### schedule *: [Schedule](zenml.config.md#zenml.config.schedule.Schedule) | None*

#### workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

### *class* zenml.models.v2.core.trigger.TriggerResponseResources(\*, action: [ActionResponse](#zenml.models.v2.core.action.ActionResponse), event_source: [EventSourceResponse](#zenml.models.v2.core.event_source.EventSourceResponse) | None = None, executions: [Page](zenml.models.v2.base.md#id327)[[TriggerExecutionResponse](zenml.models.md#zenml.models.TriggerExecutionResponse)], \*\*extra_data: Any)

Bases: [`WorkspaceScopedResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedResponseResources)

Class for all resource models associated with the trigger entity.

#### action *: [ActionResponse](zenml.models.md#zenml.models.ActionResponse)*

#### event_source *: [EventSourceResponse](zenml.models.md#zenml.models.EventSourceResponse) | None*

#### executions *: [Page](zenml.models.v2.base.md#id327)[[TriggerExecutionResponse](zenml.models.md#zenml.models.TriggerExecutionResponse)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'action': FieldInfo(annotation=ActionResponse, required=True, title='The action that is executed by this trigger.'), 'event_source': FieldInfo(annotation=Union[EventSourceResponse, NoneType], required=False, default=None, title='The event source that activates this trigger. Not set if the trigger is activated by a schedule.'), 'executions': FieldInfo(annotation=Page[TriggerExecutionResponse], required=True, title='The executions of this trigger.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.trigger.TriggerUpdate(\*, name: Annotated[str | None, MaxLen(max_length=255)] = None, description: Annotated[str | None, MaxLen(max_length=255)] = None, event_filter: Dict[str, Any] | None = None, schedule: [Schedule](zenml.config.md#zenml.config.schedule.Schedule) | None = None, is_active: bool | None = None)

Bases: [`BaseUpdate`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseUpdate)

Update model for triggers.

#### description *: str | None*

#### event_filter *: Dict[str, Any] | None*

#### is_active *: bool | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The new description for the trigger.', metadata=[MaxLen(max_length=255)]), 'event_filter': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, title='New filter applied to events that activate this trigger. Only valid if the trigger is already configured to be activated by an event source.'), 'is_active': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, title='The new status of the trigger.'), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The new name for the trigger.', metadata=[MaxLen(max_length=255)]), 'schedule': FieldInfo(annotation=Union[Schedule, NoneType], required=False, default=None, title='The updated schedule for the trigger. Only valid if the trigger is already configured to be activated by a schedule.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

#### schedule *: [Schedule](zenml.config.md#zenml.config.schedule.Schedule) | None*

## zenml.models.v2.core.trigger_execution module

Collection of all models concerning trigger executions.

### *class* zenml.models.v2.core.trigger_execution.TriggerExecutionFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None, trigger_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None)

Bases: [`WorkspaceScopedFilter`](zenml.models.v2.base.md#zenml.models.v2.base.scoped.WorkspaceScopedFilter)

Model to enable advanced filtering of all trigger executions.

#### created *: datetime | str | None*

#### id *: UUID | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'trigger_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='ID of the trigger of the execution.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### page *: int*

#### scope_workspace *: UUID | None*

#### size *: int*

#### sort_by *: str*

#### trigger_id *: UUID | str | None*

#### updated *: datetime | str | None*

### *class* zenml.models.v2.core.trigger_execution.TriggerExecutionRequest(\*, trigger: UUID, event_metadata: Dict[str, Any] = {})

Bases: [`BaseRequest`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseRequest)

Model for creating a new Trigger execution.

#### event_metadata *: Dict[str, Any]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'event_metadata': FieldInfo(annotation=Dict[str, Any], required=False, default={}), 'trigger': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### trigger *: UUID*

### *class* zenml.models.v2.core.trigger_execution.TriggerExecutionResponse(\*, body: [TriggerExecutionResponseBody](#zenml.models.v2.core.trigger_execution.TriggerExecutionResponseBody) | None = None, metadata: [TriggerExecutionResponseMetadata](#zenml.models.v2.core.trigger_execution.TriggerExecutionResponseMetadata) | None = None, resources: [TriggerExecutionResponseResources](#zenml.models.v2.core.trigger_execution.TriggerExecutionResponseResources) | None = None, id: UUID, permission_denied: bool = False)

Bases: `BaseIdentifiedResponse[TriggerExecutionResponseBody, TriggerExecutionResponseMetadata, TriggerExecutionResponseResources]`

Response model for trigger executions.

#### body *: 'AnyBody' | None*

#### *property* event_metadata *: Dict[str, Any]*

The event_metadata property.

Returns:
: the value of the property.

#### get_hydrated_version() → [TriggerExecutionResponse](#zenml.models.v2.core.trigger_execution.TriggerExecutionResponse)

Get the hydrated version of this trigger execution.

Returns:
: an instance of the same entity with the metadata field attached.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[TriggerExecutionResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[TriggerExecutionResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[TriggerExecutionResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* trigger *: [TriggerResponse](zenml.models.md#zenml.models.TriggerResponse)*

The trigger property.

Returns:
: the value of the property.

### *class* zenml.models.v2.core.trigger_execution.TriggerExecutionResponseBody(\*, created: datetime, updated: datetime)

Bases: [`BaseDatedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseDatedResponseBody)

Response body for trigger executions.

#### created *: datetime*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### updated *: datetime*

### *class* zenml.models.v2.core.trigger_execution.TriggerExecutionResponseMetadata(\*, event_metadata: Dict[str, Any] = {})

Bases: [`BaseResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseMetadata)

Response metadata for trigger executions.

#### event_metadata *: Dict[str, Any]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'event_metadata': FieldInfo(annotation=Dict[str, Any], required=False, default={})}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.trigger_execution.TriggerExecutionResponseResources(\*, trigger: [TriggerResponse](#zenml.models.v2.core.trigger.TriggerResponse), \*\*extra_data: Any)

Bases: [`BaseResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseResources)

Class for all resource models associated with the trigger entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'trigger': FieldInfo(annotation=TriggerResponse, required=True, title='The event source that activates this trigger.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### trigger *: [TriggerResponse](zenml.models.md#zenml.models.TriggerResponse)*

## zenml.models.v2.core.user module

Models representing users.

### *class* zenml.models.v2.core.user.UserBase(\*, email: Annotated[str | None, MaxLen(max_length=255)] = None, email_opted_in: bool | None = None, password: Annotated[str | None, MaxLen(max_length=255)] = None, activation_token: Annotated[str | None, MaxLen(max_length=255)] = None, external_user_id: UUID | None = None, user_metadata: Dict[str, Any] | None = None)

Bases: `BaseModel`

Base model for users.

#### activation_token *: str | None*

#### create_hashed_activation_token() → str | None

Hashes the activation token.

Returns:
: The hashed activation token.

#### create_hashed_password() → str | None

Hashes the password.

Returns:
: The hashed password.

#### email *: str | None*

#### email_opted_in *: bool | None*

#### external_user_id *: UUID | None*

#### generate_activation_token() → str

Generates and stores a new activation token.

Returns:
: The generated activation token.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'activation_token': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, metadata=[MaxLen(max_length=255)]), 'email': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The email address associated with the account.', metadata=[MaxLen(max_length=255)]), 'email_opted_in': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, title='Whether the user agreed to share their email. Only relevant for user accounts', description='\`null\` if not answered, \`true\` if agreed, \`false\` if skipped.'), 'external_user_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The external user ID associated with the account.'), 'password': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='A password for the user.', metadata=[MaxLen(max_length=255)]), 'user_metadata': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, title='The metadata associated with the user.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### password *: str | None*

#### user_metadata *: Dict[str, Any] | None*

### *class* zenml.models.v2.core.user.UserFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, name: str | None = None, full_name: str | None = None, email: str | None = None, active: Annotated[bool | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, email_opted_in: Annotated[bool | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, external_user_id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None)

Bases: [`BaseFilter`](zenml.models.v2.base.md#zenml.models.v2.base.filter.BaseFilter)

Model to enable advanced filtering of all Users.

#### active *: bool | str | None*

#### apply_filter(query: AnyQuery, table: Type[AnySchema]) → AnyQuery

Override to filter out service accounts from the query.

Args:
: query: The query to which to apply the filter.
  table: The query table.

Returns:
: The query with filter applied.

#### created *: datetime | str | None*

#### email *: str | None*

#### email_opted_in *: bool | str | None*

#### external_user_id *: UUID | str | None*

#### full_name *: str | None*

#### id *: UUID | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'active': FieldInfo(annotation=Union[bool, str, NoneType], required=False, default=None, description='Whether the user is active', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'email': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Email of the user'), 'email_opted_in': FieldInfo(annotation=Union[bool, str, NoneType], required=False, default=None, description='Whether the user has opted in to emails', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'external_user_id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, title='The external user ID associated with the account.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'full_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Full Name of the user'), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Name of the user'), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str | None*

#### page *: int*

#### size *: int*

#### sort_by *: str*

#### updated *: datetime | str | None*

### *class* zenml.models.v2.core.user.UserRequest(\*, email: Annotated[str | None, MaxLen(max_length=255)] = None, email_opted_in: bool | None = None, password: Annotated[str | None, MaxLen(max_length=255)] = None, activation_token: Annotated[str | None, MaxLen(max_length=255)] = None, external_user_id: UUID | None = None, user_metadata: Dict[str, Any] | None = None, name: Annotated[str, MaxLen(max_length=255)], full_name: Annotated[str, MaxLen(max_length=255)] = '', is_admin: bool, active: bool = False)

Bases: [`UserBase`](#zenml.models.v2.core.user.UserBase), [`BaseRequest`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseRequest)

Request model for users.

#### ANALYTICS_FIELDS *: ClassVar[List[str]]* *= ['name', 'full_name', 'active', 'email_opted_in']*

#### activation_token *: str | None*

#### active *: bool*

#### email *: str | None*

#### email_opted_in *: bool | None*

#### external_user_id *: UUID | None*

#### full_name *: str*

#### is_admin *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'activation_token': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, metadata=[MaxLen(max_length=255)]), 'active': FieldInfo(annotation=bool, required=False, default=False, title='Whether the account is active.'), 'email': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The email address associated with the account.', metadata=[MaxLen(max_length=255)]), 'email_opted_in': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, title='Whether the user agreed to share their email. Only relevant for user accounts', description='\`null\` if not answered, \`true\` if agreed, \`false\` if skipped.'), 'external_user_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The external user ID associated with the account.'), 'full_name': FieldInfo(annotation=str, required=False, default='', title='The full name for the account owner. Only relevant for user accounts.', metadata=[MaxLen(max_length=255)]), 'is_admin': FieldInfo(annotation=bool, required=True, title='Whether the account is an administrator.'), 'name': FieldInfo(annotation=str, required=True, title='The unique username for the account.', metadata=[MaxLen(max_length=255)]), 'password': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='A password for the user.', metadata=[MaxLen(max_length=255)]), 'user_metadata': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, title='The metadata associated with the user.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### password *: str | None*

#### user_metadata *: Dict[str, Any] | None*

### *class* zenml.models.v2.core.user.UserResponse(\*, body: [UserResponseBody](#zenml.models.v2.core.user.UserResponseBody) | None = None, metadata: [UserResponseMetadata](#zenml.models.v2.core.user.UserResponseMetadata) | None = None, resources: [UserResponseResources](#zenml.models.v2.core.user.UserResponseResources) | None = None, id: UUID, permission_denied: bool = False, name: Annotated[str, MaxLen(max_length=255)])

Bases: `BaseIdentifiedResponse[UserResponseBody, UserResponseMetadata, UserResponseResources]`

Response model for user and service accounts.

This returns the activation_token that is required for the
user-invitation-flow of the frontend. The email is returned optionally as
well for use by the analytics on the client-side.

#### ANALYTICS_FIELDS *: ClassVar[List[str]]* *= ['name', 'full_name', 'active', 'email_opted_in', 'is_service_account']*

#### *property* activation_token *: str | None*

The activation_token property.

Returns:
: the value of the property.

#### *property* active *: bool*

The active property.

Returns:
: the value of the property.

#### body *: 'AnyBody' | None*

#### *property* email *: str | None*

The email property.

Returns:
: the value of the property.

#### *property* email_opted_in *: bool | None*

The email_opted_in property.

Returns:
: the value of the property.

#### *property* external_user_id *: UUID | None*

The external_user_id property.

Returns:
: the value of the property.

#### *property* full_name *: str*

The full_name property.

Returns:
: the value of the property.

#### get_hydrated_version() → [UserResponse](#zenml.models.v2.core.user.UserResponse)

Get the hydrated version of this user.

Returns:
: an instance of the same entity with the metadata field attached.

#### id *: UUID*

#### *property* is_admin *: bool*

The is_admin property.

Returns:
: Whether the user is an admin.

#### *property* is_service_account *: bool*

The is_service_account property.

Returns:
: the value of the property.

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[UserResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[UserResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='The unique username for the account.', metadata=[MaxLen(max_length=255)]), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[UserResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str*

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* user_metadata *: Dict[str, Any]*

The user_metadata property.

Returns:
: the value of the property.

### *class* zenml.models.v2.core.user.UserResponseBody(\*, created: datetime, updated: datetime, active: bool = False, activation_token: Annotated[str | None, MaxLen(max_length=255)] = None, full_name: Annotated[str, MaxLen(max_length=255)] = '', email_opted_in: bool | None = None, is_service_account: bool, is_admin: bool)

Bases: [`BaseDatedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseDatedResponseBody)

Response body for users.

#### activation_token *: str | None*

#### active *: bool*

#### created *: datetime*

#### email_opted_in *: bool | None*

#### full_name *: str*

#### is_admin *: bool*

#### is_service_account *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'activation_token': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The activation token for the user. Only relevant for user accounts.', metadata=[MaxLen(max_length=255)]), 'active': FieldInfo(annotation=bool, required=False, default=False, title='Whether the account is active.'), 'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'email_opted_in': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, title='Whether the user agreed to share their email. Only relevant for user accounts', description='\`null\` if not answered, \`true\` if agreed, \`false\` if skipped.'), 'full_name': FieldInfo(annotation=str, required=False, default='', title='The full name for the account owner. Only relevant for user accounts.', metadata=[MaxLen(max_length=255)]), 'is_admin': FieldInfo(annotation=bool, required=True, title='Whether the account is an administrator.'), 'is_service_account': FieldInfo(annotation=bool, required=True, title='Indicates whether this is a service account or a user account.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### updated *: datetime*

### *class* zenml.models.v2.core.user.UserResponseMetadata(\*, email: Annotated[str | None, MaxLen(max_length=255)] = '', external_user_id: UUID | None = None, user_metadata: Dict[str, Any] = {})

Bases: [`BaseResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseMetadata)

Response metadata for users.

#### email *: str | None*

#### external_user_id *: UUID | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'email': FieldInfo(annotation=Union[str, NoneType], required=False, default='', title='The email address associated with the account. Only relevant for user accounts.', metadata=[MaxLen(max_length=255)]), 'external_user_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The external user ID associated with the account. Only relevant for user accounts.'), 'user_metadata': FieldInfo(annotation=Dict[str, Any], required=False, default={}, title='The metadata associated with the user.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### user_metadata *: Dict[str, Any]*

### *class* zenml.models.v2.core.user.UserResponseResources(\*\*extra_data: Any)

Bases: [`BaseResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseResources)

Class for all resource models associated with the user entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.user.UserUpdate(\*, email: Annotated[str | None, MaxLen(max_length=255)] = None, email_opted_in: bool | None = None, password: Annotated[str | None, MaxLen(max_length=255)] = None, activation_token: Annotated[str | None, MaxLen(max_length=255)] = None, external_user_id: UUID | None = None, user_metadata: Dict[str, Any] | None = None, name: Annotated[str | None, MaxLen(max_length=255)] = None, full_name: Annotated[str | None, MaxLen(max_length=255)] = None, is_admin: bool | None = None, active: bool | None = None, old_password: Annotated[str | None, MaxLen(max_length=255)] = None)

Bases: [`UserBase`](#zenml.models.v2.core.user.UserBase), [`BaseZenModel`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseZenModel)

Update model for users.

#### activation_token *: str | None*

#### active *: bool | None*

#### create_copy(exclude: AbstractSet[str]) → [UserUpdate](#zenml.models.v2.core.user.UserUpdate)

Create a copy of the current instance.

Args:
: exclude: Fields to exclude from the copy.

Returns:
: A copy of the current instance.

#### email *: str | None*

#### email_opted_in *: bool | None*

#### external_user_id *: UUID | None*

#### full_name *: str | None*

#### is_admin *: bool | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'activation_token': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, metadata=[MaxLen(max_length=255)]), 'active': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, title='Whether the account is active.'), 'email': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The email address associated with the account.', metadata=[MaxLen(max_length=255)]), 'email_opted_in': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, title='Whether the user agreed to share their email. Only relevant for user accounts', description='\`null\` if not answered, \`true\` if agreed, \`false\` if skipped.'), 'external_user_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The external user ID associated with the account.'), 'full_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The full name for the account owner. Only relevant for user accounts.', metadata=[MaxLen(max_length=255)]), 'is_admin': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, title='Whether the account is an administrator.'), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The unique username for the account.', metadata=[MaxLen(max_length=255)]), 'old_password': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The previous password for the user. Only relevant for user accounts. Required when updating the password.', metadata=[MaxLen(max_length=255)]), 'password': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='A password for the user.', metadata=[MaxLen(max_length=255)]), 'user_metadata': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None, title='The metadata associated with the user.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

#### old_password *: str | None*

#### password *: str | None*

#### user_email_updates() → [UserUpdate](#zenml.models.v2.core.user.UserUpdate)

Validate that the UserUpdateModel conforms to the email-opt-in-flow.

Returns:
: The validated values.

Raises:
: ValueError: If the email was not provided when the email_opted_in
  : field was set to True.

#### user_metadata *: Dict[str, Any] | None*

## zenml.models.v2.core.workspace module

Models representing workspaces.

### *class* zenml.models.v2.core.workspace.WorkspaceFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, name: str | None = None)

Bases: [`BaseFilter`](zenml.models.v2.base.md#zenml.models.v2.base.filter.BaseFilter)

Model to enable advanced filtering of all Workspaces.

#### created *: datetime | str | None*

#### id *: UUID | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Name of the workspace'), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str | None*

#### page *: int*

#### size *: int*

#### sort_by *: str*

#### updated *: datetime | str | None*

### *class* zenml.models.v2.core.workspace.WorkspaceRequest(\*, name: Annotated[str, MaxLen(max_length=255)], description: Annotated[str, MaxLen(max_length=255)] = '')

Bases: [`BaseRequest`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseRequest)

Request model for workspaces.

#### description *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'description': FieldInfo(annotation=str, required=False, default='', title='The description of the workspace.', metadata=[MaxLen(max_length=255)]), 'name': FieldInfo(annotation=str, required=True, title='The unique name of the workspace.', metadata=[MaxLen(max_length=255)])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

### *class* zenml.models.v2.core.workspace.WorkspaceResponse(\*, body: [WorkspaceResponseBody](#zenml.models.v2.core.workspace.WorkspaceResponseBody) | None = None, metadata: [WorkspaceResponseMetadata](#zenml.models.v2.core.workspace.WorkspaceResponseMetadata) | None = None, resources: [WorkspaceResponseResources](#zenml.models.v2.core.workspace.WorkspaceResponseResources) | None = None, id: UUID, permission_denied: bool = False, name: Annotated[str, MaxLen(max_length=255)])

Bases: `BaseIdentifiedResponse[WorkspaceResponseBody, WorkspaceResponseMetadata, WorkspaceResponseResources]`

Response model for workspaces.

#### body *: 'AnyBody' | None*

#### *property* description *: str*

The description property.

Returns:
: the value of the property.

#### get_hydrated_version() → [WorkspaceResponse](#zenml.models.v2.core.workspace.WorkspaceResponse)

Get the hydrated version of this workspace.

Returns:
: an instance of the same entity with the metadata field attached.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[WorkspaceResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[WorkspaceResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='The unique name of the workspace.', metadata=[MaxLen(max_length=255)]), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[WorkspaceResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str*

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

### *class* zenml.models.v2.core.workspace.WorkspaceResponseBody(\*, created: datetime, updated: datetime)

Bases: [`BaseDatedResponseBody`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseDatedResponseBody)

Response body for workspaces.

#### created *: datetime*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### updated *: datetime*

### *class* zenml.models.v2.core.workspace.WorkspaceResponseMetadata(\*, description: Annotated[str, MaxLen(max_length=255)] = '')

Bases: [`BaseResponseMetadata`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseMetadata)

Response metadata for workspaces.

#### description *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'description': FieldInfo(annotation=str, required=False, default='', title='The description of the workspace.', metadata=[MaxLen(max_length=255)])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.workspace.WorkspaceResponseResources(\*\*extra_data: Any)

Bases: [`BaseResponseResources`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseResponseResources)

Class for all resource models associated with the workspace entity.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.core.workspace.WorkspaceUpdate(\*, name: Annotated[str | None, MaxLen(max_length=255)] = None, description: Annotated[str | None, MaxLen(max_length=255)] = None)

Bases: [`BaseUpdate`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseUpdate)

Update model for workspaces.

#### description *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The description of the workspace.', metadata=[MaxLen(max_length=255)]), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The unique name of the workspace.', metadata=[MaxLen(max_length=255)])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

## Module contents
