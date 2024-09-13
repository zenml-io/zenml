# zenml.models.v2.misc package

## Submodules

## zenml.models.v2.misc.auth_models module

Models representing OAuth2 requests and responses.

### *class* zenml.models.v2.misc.auth_models.OAuthDeviceAuthorizationRequest(\*, client_id: UUID)

Bases: `BaseModel`

OAuth2 device authorization grant request.

#### client_id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'client_id': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.misc.auth_models.OAuthDeviceAuthorizationResponse(\*, device_code: str, user_code: str, verification_uri: str, verification_uri_complete: str | None = None, expires_in: int, interval: int)

Bases: `BaseModel`

OAuth2 device authorization grant response.

#### device_code *: str*

#### expires_in *: int*

#### interval *: int*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'device_code': FieldInfo(annotation=str, required=True), 'expires_in': FieldInfo(annotation=int, required=True), 'interval': FieldInfo(annotation=int, required=True), 'user_code': FieldInfo(annotation=str, required=True), 'verification_uri': FieldInfo(annotation=str, required=True), 'verification_uri_complete': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### user_code *: str*

#### verification_uri *: str*

#### verification_uri_complete *: str | None*

### *class* zenml.models.v2.misc.auth_models.OAuthDeviceTokenRequest(\*, grant_type: str = OAuthGrantTypes.OAUTH_DEVICE_CODE, client_id: UUID, device_code: str)

Bases: `BaseModel`

OAuth2 device authorization grant request.

#### client_id *: UUID*

#### device_code *: str*

#### grant_type *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'client_id': FieldInfo(annotation=UUID, required=True), 'device_code': FieldInfo(annotation=str, required=True), 'grant_type': FieldInfo(annotation=str, required=False, default=<OAuthGrantTypes.OAUTH_DEVICE_CODE: 'urn:ietf:params:oauth:grant-type:device_code'>)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.misc.auth_models.OAuthDeviceUserAgentHeader(\*, hostname: str | None = None, os: str | None = None, python_version: str | None = None, zenml_version: str | None = None)

Bases: `BaseModel`

OAuth2 device user agent header.

#### *classmethod* decode(header_str: str) → [OAuthDeviceUserAgentHeader](#zenml.models.v2.misc.auth_models.OAuthDeviceUserAgentHeader)

Decode the user agent header.

Args:
: header_str: The user agent header string value.

Returns:
: The decoded user agent header.

#### encode() → str

Encode the user agent header.

Returns:
: The encoded user agent header.

#### hostname *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'hostname': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'os': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'python_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'zenml_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### os *: str | None*

#### python_version *: str | None*

#### zenml_version *: str | None*

### *class* zenml.models.v2.misc.auth_models.OAuthDeviceVerificationRequest(\*, user_code: str, trusted_device: bool = False)

Bases: `BaseModel`

OAuth2 device authorization verification request.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'trusted_device': FieldInfo(annotation=bool, required=False, default=False), 'user_code': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### trusted_device *: bool*

#### user_code *: str*

### *class* zenml.models.v2.misc.auth_models.OAuthRedirectResponse(\*, authorization_url: str)

Bases: `BaseModel`

Redirect response.

#### authorization_url *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'authorization_url': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.misc.auth_models.OAuthTokenResponse(\*, access_token: str, token_type: str, expires_in: int | None = None, refresh_token: str | None = None, scope: str | None = None)

Bases: `BaseModel`

OAuth2 device authorization token response.

#### access_token *: str*

#### expires_in *: int | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'access_token': FieldInfo(annotation=str, required=True), 'expires_in': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'refresh_token': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'scope': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'token_type': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### refresh_token *: str | None*

#### scope *: str | None*

#### token_type *: str*

## zenml.models.v2.misc.build_item module

Model definition for pipeline build item.

### *class* zenml.models.v2.misc.build_item.BuildItem(\*, image: str, dockerfile: str | None = None, requirements: str | None = None, settings_checksum: str | None = None, contains_code: bool = True, requires_code_download: bool = False)

Bases: `BaseModel`

Pipeline build item.

Attributes:
: image: The image name or digest.
  dockerfile: The contents of the Dockerfile used to build the image.
  requirements: The pip requirements installed in the image. This is a
  <br/>
  > string consisting of multiple concatenated requirements.txt files.
  <br/>
  settings_checksum: Checksum of the settings used for the build.
  contains_code: Whether the image contains user files.
  requires_code_download: Whether the image needs to download files.

#### contains_code *: bool*

#### dockerfile *: str | None*

#### image *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'contains_code': FieldInfo(annotation=bool, required=False, default=True, title='Whether the image contains user files.'), 'dockerfile': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The dockerfile used to build the image.'), 'image': FieldInfo(annotation=str, required=True, title='The image name or digest.'), 'requirements': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The pip requirements installed in the image.'), 'requires_code_download': FieldInfo(annotation=bool, required=False, default=False, title='Whether the image needs to download files.'), 'settings_checksum': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The checksum of the build settings.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### requirements *: str | None*

#### requires_code_download *: bool*

#### settings_checksum *: str | None*

## zenml.models.v2.misc.external_user module

Models representing users.

### *class* zenml.models.v2.misc.external_user.ExternalUserModel(\*, id: UUID, email: str, name: str | None = None, is_admin: bool = False)

Bases: `BaseModel`

External user model.

#### email *: str*

#### id *: UUID*

#### is_admin *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'email': FieldInfo(annotation=str, required=True), 'id': FieldInfo(annotation=UUID, required=True), 'is_admin': FieldInfo(annotation=bool, required=False, default=False), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

## zenml.models.v2.misc.info_models module

Models representing full stack requests.

### *class* zenml.models.v2.misc.info_models.ComponentInfo(\*, flavor: str, service_connector_index: int | None = None, service_connector_resource_id: str | None = None, configuration: Dict[str, Any] = {})

Bases: `BaseModel`

Information about each stack components when creating a full stack.

#### configuration *: Dict[str, Any]*

#### flavor *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'configuration': FieldInfo(annotation=Dict[str, Any], required=False, default={}), 'flavor': FieldInfo(annotation=str, required=True), 'service_connector_index': FieldInfo(annotation=Union[int, NoneType], required=False, default=None, title='The id of the service connector from the list \`service_connectors\`.', description='The id of the service connector from the list \`service_connectors\` from \`FullStackRequest\`.'), 'service_connector_resource_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### service_connector_index *: int | None*

#### service_connector_resource_id *: str | None*

### *class* zenml.models.v2.misc.info_models.ResourcesInfo(\*, flavor: str, flavor_display_name: str, required_configuration: Dict[str, str] = {}, use_resource_value_as_fixed_config: bool = False, accessible_by_service_connector: List[str], connected_through_service_connector: List[[ComponentResponse](zenml.models.v2.core.md#zenml.models.v2.core.component.ComponentResponse)])

Bases: `BaseModel`

Information about the resources needed for CLI and UI.

#### accessible_by_service_connector *: List[str]*

#### connected_through_service_connector *: List[[ComponentResponse](zenml.models.md#zenml.models.ComponentResponse)]*

#### flavor *: str*

#### flavor_display_name *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'accessible_by_service_connector': FieldInfo(annotation=List[str], required=True), 'connected_through_service_connector': FieldInfo(annotation=List[ComponentResponse], required=True), 'flavor': FieldInfo(annotation=str, required=True), 'flavor_display_name': FieldInfo(annotation=str, required=True), 'required_configuration': FieldInfo(annotation=Dict[str, str], required=False, default={}), 'use_resource_value_as_fixed_config': FieldInfo(annotation=bool, required=False, default=False)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### required_configuration *: Dict[str, str]*

#### use_resource_value_as_fixed_config *: bool*

### *class* zenml.models.v2.misc.info_models.ServiceConnectorInfo(\*, type: str, auth_method: str, configuration: Dict[str, Any] = {})

Bases: `BaseModel`

Information about the service connector when creating a full stack.

#### auth_method *: str*

#### configuration *: Dict[str, Any]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'auth_method': FieldInfo(annotation=str, required=True), 'configuration': FieldInfo(annotation=Dict[str, Any], required=False, default={}), 'type': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: str*

### *class* zenml.models.v2.misc.info_models.ServiceConnectorResourcesInfo(\*, connector_type: str, components_resources_info: Dict[[StackComponentType](zenml.md#zenml.enums.StackComponentType), List[[ResourcesInfo](#zenml.models.v2.misc.info_models.ResourcesInfo)]])

Bases: `BaseModel`

Information about the service connector resources needed for CLI and UI.

#### components_resources_info *: Dict[[StackComponentType](zenml.md#zenml.enums.StackComponentType), List[[ResourcesInfo](#zenml.models.v2.misc.info_models.ResourcesInfo)]]*

#### connector_type *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'components_resources_info': FieldInfo(annotation=Dict[StackComponentType, List[ResourcesInfo]], required=True), 'connector_type': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## zenml.models.v2.misc.loaded_visualization module

Model representing loaded visualizations.

### *class* zenml.models.v2.misc.loaded_visualization.LoadedVisualization(\*, type: [VisualizationType](zenml.md#zenml.enums.VisualizationType), value: Annotated[str | bytes, \_PydanticGeneralMetadata(union_mode='left_to_right')])

Bases: `BaseModel`

Model for loaded visualizations.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'type': FieldInfo(annotation=VisualizationType, required=True), 'value': FieldInfo(annotation=Union[str, bytes], required=True, metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: [VisualizationType](zenml.md#zenml.enums.VisualizationType)*

#### value *: str | bytes*

## zenml.models.v2.misc.server_models module

Model definitions for ZenML servers.

### *class* zenml.models.v2.misc.server_models.ServerDatabaseType(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: [`StrEnum`](zenml.utils.md#zenml.utils.enum_utils.StrEnum)

Enum for server database types.

#### MYSQL *= 'mysql'*

#### OTHER *= 'other'*

#### SQLITE *= 'sqlite'*

### *class* zenml.models.v2.misc.server_models.ServerDeploymentType(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: [`StrEnum`](zenml.utils.md#zenml.utils.enum_utils.StrEnum)

Enum for server deployment types.

#### ALPHA *= 'alpha'*

#### AWS *= 'aws'*

#### AZURE *= 'azure'*

#### CLOUD *= 'cloud'*

#### DOCKER *= 'docker'*

#### GCP *= 'gcp'*

#### HF_SPACES *= 'hf_spaces'*

#### KUBERNETES *= 'kubernetes'*

#### LOCAL *= 'local'*

#### OTHER *= 'other'*

#### SANDBOX *= 'sandbox'*

### *class* zenml.models.v2.misc.server_models.ServerModel(\*, id: UUID = None, version: str, active: bool = True, debug: bool = False, deployment_type: [ServerDeploymentType](#zenml.models.v2.misc.server_models.ServerDeploymentType) = ServerDeploymentType.OTHER, database_type: [ServerDatabaseType](#zenml.models.v2.misc.server_models.ServerDatabaseType) = ServerDatabaseType.OTHER, secrets_store_type: [SecretsStoreType](zenml.md#zenml.enums.SecretsStoreType) = SecretsStoreType.NONE, auth_scheme: [AuthScheme](zenml.md#zenml.enums.AuthScheme), server_url: str = '', dashboard_url: str = '', analytics_enabled: bool = True, metadata: Dict[str, str] = {}, use_legacy_dashboard: bool = False, last_user_activity: datetime | None = None)

Bases: `BaseModel`

Domain model for ZenML servers.

#### active *: bool*

#### analytics_enabled *: bool*

#### auth_scheme *: [AuthScheme](zenml.md#zenml.enums.AuthScheme)*

#### dashboard_url *: str*

#### database_type *: [ServerDatabaseType](#zenml.models.v2.misc.server_models.ServerDatabaseType)*

#### debug *: bool*

#### deployment_type *: [ServerDeploymentType](#zenml.models.v2.misc.server_models.ServerDeploymentType)*

#### id *: UUID*

#### is_local() → bool

Return whether the server is running locally.

Returns:
: True if the server is running locally, False otherwise.

#### last_user_activity *: datetime | None*

#### metadata *: Dict[str, str]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'active': FieldInfo(annotation=bool, required=False, default=True, title='Flag to indicate whether the server is active.'), 'analytics_enabled': FieldInfo(annotation=bool, required=False, default=True, title='Enable server-side analytics.'), 'auth_scheme': FieldInfo(annotation=AuthScheme, required=True, title='The authentication scheme that the server is using.'), 'dashboard_url': FieldInfo(annotation=str, required=False, default='', title='The URL where the ZenML dashboard is reachable. If not specified, the \`server_url\` value will be used instead.'), 'database_type': FieldInfo(annotation=ServerDatabaseType, required=False, default=<ServerDatabaseType.OTHER: 'other'>, title='The database type that the server is using.'), 'debug': FieldInfo(annotation=bool, required=False, default=False, title='Flag to indicate whether ZenML is running on debug mode.'), 'deployment_type': FieldInfo(annotation=ServerDeploymentType, required=False, default=<ServerDeploymentType.OTHER: 'other'>, title='The ZenML server deployment type.'), 'id': FieldInfo(annotation=UUID, required=False, default_factory=uuid4, title='The unique server id.'), 'last_user_activity': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None, title='Timestamp of latest user activity traced on the server.'), 'metadata': FieldInfo(annotation=Dict[str, str], required=False, default={}, title='The metadata associated with the server.'), 'secrets_store_type': FieldInfo(annotation=SecretsStoreType, required=False, default=<SecretsStoreType.NONE: 'none'>, title='The type of secrets store that the server is using.'), 'server_url': FieldInfo(annotation=str, required=False, default='', title='The URL where the ZenML server API is reachable. If not specified, the clients will use the same URL used to connect them to the ZenML server.'), 'use_legacy_dashboard': FieldInfo(annotation=bool, required=False, default=False, title='Flag to indicate whether the server is using the legacy dashboard.'), 'version': FieldInfo(annotation=str, required=True, title='The ZenML version that the server is running.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### secrets_store_type *: [SecretsStoreType](zenml.md#zenml.enums.SecretsStoreType)*

#### server_url *: str*

#### use_legacy_dashboard *: bool*

#### version *: str*

## zenml.models.v2.misc.service_connector_type module

Model definitions for ZenML service connectors.

### *class* zenml.models.v2.misc.service_connector_type.AuthenticationMethodModel(config_class: Type[BaseModel] | None = None, \*, name: str, auth_method: Annotated[str, MaxLen(max_length=255)], description: str = '', config_schema: Dict[str, Any] = None, min_expiration_seconds: int | None = None, max_expiration_seconds: int | None = None, default_expiration_seconds: int | None = None)

Bases: `BaseModel`

Authentication method specification.

Describes the schema for the configuration and secrets that need to be
provided to configure an authentication method.

#### auth_method *: str*

#### *property* config_class *: Type[BaseModel] | None*

Get the configuration class for the authentication method.

Returns:
: The configuration class for the authentication method.

#### config_schema *: Dict[str, Any]*

#### default_expiration_seconds *: int | None*

#### description *: str*

#### max_expiration_seconds *: int | None*

#### min_expiration_seconds *: int | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'auth_method': FieldInfo(annotation=str, required=True, title='The name of the authentication method.', metadata=[MaxLen(max_length=255)]), 'config_schema': FieldInfo(annotation=Dict[str, Any], required=False, default_factory=dict, title='The JSON schema of the configuration for this authentication method.'), 'default_expiration_seconds': FieldInfo(annotation=Union[int, NoneType], required=False, default=None, title="The default number of seconds that the authentication session is valid for. Set to None for authentication sessions and long-lived credentials that don't expire."), 'description': FieldInfo(annotation=str, required=False, default='', title='A description of the authentication method.'), 'max_expiration_seconds': FieldInfo(annotation=Union[int, NoneType], required=False, default=None, title="The maximum number of seconds that the authentication session can be configured to be valid for. Set to None for authentication sessions and long-lived credentials that don't expire."), 'min_expiration_seconds': FieldInfo(annotation=Union[int, NoneType], required=False, default=None, title="The minimum number of seconds that the authentication session can be configured to be valid for. Set to None for authentication sessions and long-lived credentials that don't expire."), 'name': FieldInfo(annotation=str, required=True, title='User readable name for the authentication method.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

This function is meant to behave like a BaseModel method to initialise private attributes.

It takes context as an argument since that’s what pydantic-core passes when calling it.

Args:
: self: The BaseModel instance.
  context: The context.

#### name *: str*

#### supports_temporary_credentials() → bool

Check if the authentication method supports temporary credentials.

Returns:
: True if the authentication method supports temporary credentials,
  False otherwise.

#### validate_expiration(expiration_seconds: int | None) → int | None

Validate the expiration time.

Args:
: expiration_seconds: The expiration time in seconds. If None, the
  : default expiration time is used, if applicable.

Returns:
: The expiration time in seconds or None if not applicable.

Raises:
: ValueError: If the expiration time is not valid.

### *class* zenml.models.v2.misc.service_connector_type.ResourceTypeModel(\*, name: str, resource_type: str, description: str = '', auth_methods: List[str], supports_instances: bool = False, logo_url: str | None = None, emoji: str | None = None)

Bases: `BaseModel`

Resource type specification.

Describes the authentication methods and resource instantiation model for
one or more resource types.

#### auth_methods *: List[str]*

#### description *: str*

#### emoji *: str | None*

#### *property* emojified_resource_type *: str*

Get the emojified resource type.

Returns:
: The emojified resource type.

#### logo_url *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'auth_methods': FieldInfo(annotation=List[str], required=True, title='The list of authentication methods that can be used to access resources of this type.'), 'description': FieldInfo(annotation=str, required=False, default='', title='A description of the resource type.'), 'emoji': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Optionally, a python-rich emoji can be attached.'), 'logo_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Optionally, a URL pointing to a png,svg or jpg file can be attached.'), 'name': FieldInfo(annotation=str, required=True, title='User readable name for the resource type.'), 'resource_type': FieldInfo(annotation=str, required=True, title='Resource type identifier.'), 'supports_instances': FieldInfo(annotation=bool, required=False, default=False, title='Specifies if a single connector instance can be used to access multiple instances of this resource type. If set to True, the connector is able to provide a list of resource IDs identifying all the resources that it can access and a resource ID needs to be explicitly configured or supplied when access to a resource is requested. If set to False, a connector instance is only able to access a single resource and a resource ID is not required to access the resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### resource_type *: str*

#### supports_instances *: bool*

### *class* zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements(\*, connector_type: str | None = None, resource_type: str, resource_id_attr: str | None = None)

Bases: `BaseModel`

Service connector requirements.

Describes requirements that a service connector consumer has for a
service connector instance that it needs in order to access a resource.

Attributes:
: connector_type: The type of service connector that is required. If
  : omitted, any service connector type can be used.
  <br/>
  resource_type: The type of resource that the service connector instance
  : must be able to access.
  <br/>
  resource_id_attr: The name of an attribute in the stack component
  : configuration that contains the resource ID of the resource that
    the service connector instance must be able to access.

#### connector_type *: str | None*

#### is_satisfied_by(connector: [ServiceConnectorResponse](zenml.models.md#zenml.models.ServiceConnectorResponse) | [ServiceConnectorRequest](zenml.models.md#zenml.models.ServiceConnectorRequest), component: [ComponentResponse](zenml.models.md#zenml.models.ComponentResponse) | [ComponentBase](zenml.models.md#zenml.models.ComponentBase)) → Tuple[bool, str]

Check if the requirements are satisfied by a connector.

Args:
: connector: The connector to check.
  component: The stack component that the connector is associated
  <br/>
  > with.

Returns:
: True if the requirements are satisfied, False otherwise, and a
  message describing the reason for the failure.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'connector_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'resource_id_attr': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'resource_type': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### resource_id_attr *: str | None*

#### resource_type *: str*

### *class* zenml.models.v2.misc.service_connector_type.ServiceConnectorResourcesModel(\*, id: UUID | None = None, name: Annotated[str | None, MaxLen(max_length=255)] = None, connector_type: Annotated[str | [ServiceConnectorTypeModel](#zenml.models.v2.misc.service_connector_type.ServiceConnectorTypeModel), \_PydanticGeneralMetadata(union_mode='left_to_right')], resources: List[[ServiceConnectorTypedResourcesModel](#zenml.models.v2.misc.service_connector_type.ServiceConnectorTypedResourcesModel)] = None, error: str | None = None)

Bases: `BaseModel`

Service connector resources list.

Lists the resource types and resource instances that a service connector
can provide access to.

#### connector_type *: str | [ServiceConnectorTypeModel](#zenml.models.v2.misc.service_connector_type.ServiceConnectorTypeModel)*

#### *property* emojified_connector_type *: str*

Get the emojified connector type.

Returns:
: The emojified connector type.

#### error *: str | None*

#### *classmethod* from_connector_model(connector_model: [ServiceConnectorResponse](zenml.models.md#zenml.models.ServiceConnectorResponse), resource_type: str | None = None) → [ServiceConnectorResourcesModel](#zenml.models.v2.misc.service_connector_type.ServiceConnectorResourcesModel)

Initialize a resource model from a connector model.

Args:
: connector_model: The connector model.
  resource_type: The resource type to set on the resource model. If
  <br/>
  > omitted, the resource type is set according to the connector
  > model.

Returns:
: A resource list model instance.

#### get_default_resource_id() → str | None

Get the default resource ID, if included in the resource list.

The default resource ID is a resource ID supplied by the connector
implementation only for resource types that do not support multiple
instances.

Returns:
: The default resource ID, or None if no resource ID is set.

#### get_emojified_resource_types(resource_type: str | None = None) → List[str]

Get the emojified resource type.

Args:
: resource_type: The resource type to get the emojified resource type
  : for. If omitted, the emojified resource type for all resource
    types is returned.

Returns:
: The list of emojified resource types.

#### id *: UUID | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'connector_type': FieldInfo(annotation=Union[str, ServiceConnectorTypeModel], required=True, title='The type of service connector.', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'error': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='A global error message describing why the service connector instance could not authenticate to the remote service.'), 'id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='The ID of the service connector instance providing this resource.'), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='The name of the service connector instance providing this resource.', metadata=[MaxLen(max_length=255)]), 'resources': FieldInfo(annotation=List[ServiceConnectorTypedResourcesModel], required=False, default_factory=list, title='The list of resources that the service connector instance can give access to. Contains one entry for every resource type that the connector is configured for.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

#### *property* resource_types *: List[str]*

Get the resource types.

Returns:
: The resource types.

#### resources *: List[[ServiceConnectorTypedResourcesModel](#zenml.models.v2.misc.service_connector_type.ServiceConnectorTypedResourcesModel)]*

#### *property* resources_dict *: Dict[str, [ServiceConnectorTypedResourcesModel](#zenml.models.v2.misc.service_connector_type.ServiceConnectorTypedResourcesModel)]*

Get the resources as a dictionary indexed by resource type.

Returns:
: The resources as a dictionary indexed by resource type.

#### set_error(error: str, resource_type: str | None = None) → None

Set a global error message or an error for a single resource type.

Args:
: error: The error message.
  resource_type: The resource type to set the error message for. If
  <br/>
  > omitted, or if there is only one resource type involved, the
  > error message is (also) set globally.

Raises:
: KeyError: If the resource type is not found in the resources list.

#### set_resource_ids(resource_type: str, resource_ids: List[str]) → None

Set the resource IDs for a resource type.

Args:
: resource_type: The resource type to set the resource IDs for.
  resource_ids: The resource IDs to set.

Raises:
: KeyError: If the resource type is not found in the resources list.

#### *property* type *: str*

Get the connector type.

Returns:
: The connector type.

### *class* zenml.models.v2.misc.service_connector_type.ServiceConnectorTypeModel(\*, name: str, connector_type: Annotated[str, MaxLen(max_length=255)], description: str = '', resource_types: List[[ResourceTypeModel](#zenml.models.v2.misc.service_connector_type.ResourceTypeModel)], auth_methods: List[[AuthenticationMethodModel](#zenml.models.v2.misc.service_connector_type.AuthenticationMethodModel)], supports_auto_configuration: bool = False, logo_url: str | None = None, emoji: str | None = None, docs_url: str | None = None, sdk_docs_url: str | None = None, local: bool = True, remote: bool = False)

Bases: `BaseModel`

Service connector type specification.

Describes the types of resources to which the service connector can be used
to gain access and the authentication methods that are supported by the
service connector.

The connector type, resource types, resource IDs and authentication
methods can all be used as search criteria to lookup and filter service
connector instances that are compatible with the requirements of a consumer
(e.g. a stack component).

#### *property* auth_method_dict *: Dict[str, [AuthenticationMethodModel](#zenml.models.v2.misc.service_connector_type.AuthenticationMethodModel)]*

Returns a map of authentication methods to authentication method specifications.

Returns:
: A map of authentication methods to authentication method
  specifications.

#### auth_methods *: List[[AuthenticationMethodModel](#zenml.models.v2.misc.service_connector_type.AuthenticationMethodModel)]*

#### *property* connector_class *: Type[[ServiceConnector](zenml.service_connectors.md#zenml.service_connectors.service_connector.ServiceConnector)] | None*

Get the service connector class.

Returns:
: The service connector class.

#### connector_type *: str*

#### description *: str*

#### docs_url *: str | None*

#### emoji *: str | None*

#### *property* emojified_connector_type *: str*

Get the emojified connector type.

Returns:
: The emojified connector type.

#### *property* emojified_resource_types *: List[str]*

Get the emojified connector types.

Returns:
: The emojified connector types.

#### find_resource_specifications(auth_method: str, resource_type: str | None = None) → Tuple[[AuthenticationMethodModel](#zenml.models.v2.misc.service_connector_type.AuthenticationMethodModel), [ResourceTypeModel](#zenml.models.v2.misc.service_connector_type.ResourceTypeModel) | None]

Find the specifications for a configurable resource.

Validate the supplied connector configuration parameters against the
connector specification and return the matching authentication method
specification and resource specification.

Args:
: auth_method: The name of the authentication method.
  resource_type: The type of resource being configured.

Returns:
: The authentication method specification and resource specification
  for the specified authentication method and resource type.

Raises:
: KeyError: If the authentication method is not supported by the
  : connector for the specified resource type and ID.

#### local *: bool*

#### logo_url *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'auth_methods': FieldInfo(annotation=List[AuthenticationMethodModel], required=True, title='A list of specifications describing the authentication methods that are supported by the service connector, along with the configuration and secrets attributes that need to be configured for them.'), 'connector_type': FieldInfo(annotation=str, required=True, title='The type of service connector. It can be used to represent a generic resource (e.g. Docker, Kubernetes) or a group of different resources accessible through a common interface or point of access and authentication (e.g. a cloud provider or a platform).', metadata=[MaxLen(max_length=255)]), 'description': FieldInfo(annotation=str, required=False, default='', title='A description of the service connector.'), 'docs_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Optionally, a URL pointing to docs, within docs.zenml.io.'), 'emoji': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Optionally, a python-rich emoji can be attached.'), 'local': FieldInfo(annotation=bool, required=False, default=True, title='If True, the service connector is available locally.'), 'logo_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Optionally, a URL pointing to a png,svg or jpg can be attached.'), 'name': FieldInfo(annotation=str, required=True, title='User readable name for the service connector type.'), 'remote': FieldInfo(annotation=bool, required=False, default=False, title='If True, the service connector is available remotely.'), 'resource_types': FieldInfo(annotation=List[ResourceTypeModel], required=True, title='A list of resource types that the connector can be used to access.'), 'sdk_docs_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Optionally, a URL pointing to SDK docs,within sdkdocs.zenml.io.'), 'supports_auto_configuration': FieldInfo(annotation=bool, required=False, default=False, title='Models if the connector can be configured automatically based on information extracted from a local environment.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

This function is meant to behave like a BaseModel method to initialise private attributes.

It takes context as an argument since that’s what pydantic-core passes when calling it.

Args:
: self: The BaseModel instance.
  context: The context.

#### name *: str*

#### remote *: bool*

#### *property* resource_type_dict *: Dict[str, [ResourceTypeModel](#zenml.models.v2.misc.service_connector_type.ResourceTypeModel)]*

Returns a map of resource types to resource type specifications.

Returns:
: A map of resource types to resource type specifications.

#### resource_types *: List[[ResourceTypeModel](#zenml.models.v2.misc.service_connector_type.ResourceTypeModel)]*

#### sdk_docs_url *: str | None*

#### set_connector_class(connector_class: Type[[ServiceConnector](zenml.service_connectors.md#zenml.service_connectors.service_connector.ServiceConnector)]) → None

Set the service connector class.

Args:
: connector_class: The service connector class.

#### supports_auto_configuration *: bool*

#### *classmethod* validate_auth_methods(values: List[[AuthenticationMethodModel](#zenml.models.v2.misc.service_connector_type.AuthenticationMethodModel)]) → List[[AuthenticationMethodModel](#zenml.models.v2.misc.service_connector_type.AuthenticationMethodModel)]

Validate that the authentication methods are unique.

Args:
: values: The list of authentication methods.

Returns:
: The list of authentication methods.

Raises:
: ValueError: If two or more authentication method specifications
  : share the same authentication method value.

#### *classmethod* validate_resource_types(values: List[[ResourceTypeModel](#zenml.models.v2.misc.service_connector_type.ResourceTypeModel)]) → List[[ResourceTypeModel](#zenml.models.v2.misc.service_connector_type.ResourceTypeModel)]

Validate that the resource types are unique.

Args:
: values: The list of resource types.

Returns:
: The list of resource types.

Raises:
: ValueError: If two or more resource type specifications list the
  : same resource type.

### *class* zenml.models.v2.misc.service_connector_type.ServiceConnectorTypedResourcesModel(\*, resource_type: Annotated[str, MaxLen(max_length=255)], resource_ids: List[str] | None = None, error: str | None = None)

Bases: `BaseModel`

Service connector typed resources list.

Lists the resource instances that a service connector can provide
access to.

#### error *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'error': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='An error message describing why the service connector instance could not list the resources that it is configured to access.'), 'resource_ids': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None, title="The resource IDs of all resource instances that the service connector instance can be used to access. Omitted (set to None) for multi-type service connectors that didn't explicitly request to fetch resources for all resource types. Also omitted if an error occurred while listing the resource instances or if no resources are listed due to authorization issues or lack of permissions (in both cases the 'error' field is set to an error message). For resource types that do not support multiple instances, a single resource ID is listed."), 'resource_type': FieldInfo(annotation=str, required=True, title='The type of resource that the service connector instance can be used to access.', metadata=[MaxLen(max_length=255)])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### resource_ids *: List[str] | None*

#### resource_type *: str*

## zenml.models.v2.misc.stack_deployment module

Models related to cloud stack deployments.

### *class* zenml.models.v2.misc.stack_deployment.DeployedStack(\*, stack: [StackResponse](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackResponse), service_connector: [ServiceConnectorResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorResponse) | None = None)

Bases: `BaseModel`

Information about a deployed stack.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'service_connector': FieldInfo(annotation=Union[ServiceConnectorResponse, NoneType], required=False, default=None, title='The service connector for the deployed stack.', description='The service connector for the deployed stack.'), 'stack': FieldInfo(annotation=StackResponse, required=True, title='The stack that was deployed.', description='The stack that was deployed.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### service_connector *: [ServiceConnectorResponse](zenml.models.v2.core.md#zenml.models.v2.core.service_connector.ServiceConnectorResponse) | None*

#### stack *: [StackResponse](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackResponse)*

### *class* zenml.models.v2.misc.stack_deployment.StackDeploymentConfig(\*, deployment_url: str, deployment_url_text: str, configuration: str | None = None, instructions: str | None = None)

Bases: `BaseModel`

Configuration about a stack deployment.

#### configuration *: str | None*

#### deployment_url *: str*

#### deployment_url_text *: str*

#### instructions *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'configuration': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Configuration for the stack deployment that the user must manually configure into the cloud provider console.'), 'deployment_url': FieldInfo(annotation=str, required=True, title='The cloud provider console URL where the stack will be deployed.'), 'deployment_url_text': FieldInfo(annotation=str, required=True, title='A textual description for the cloud provider console URL.'), 'instructions': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Instructions for deploying the stack.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.misc.stack_deployment.StackDeploymentInfo(\*, provider: [StackDeploymentProvider](zenml.md#zenml.enums.StackDeploymentProvider), description: str, instructions: str, post_deploy_instructions: str, integrations: List[str], permissions: Dict[str, List[str]], locations: Dict[str, str], skypilot_default_regions: Dict[str, str])

Bases: `BaseModel`

Information about a stack deployment.

#### description *: str*

#### instructions *: str*

#### integrations *: List[str]*

#### locations *: Dict[str, str]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'description': FieldInfo(annotation=str, required=True, title='The description of the stack deployment.', description='The description of the stack deployment.'), 'instructions': FieldInfo(annotation=str, required=True, title='The instructions for deploying the stack.', description='The instructions for deploying the stack.'), 'integrations': FieldInfo(annotation=List[str], required=True, title='ZenML integrations required for the stack.', description='The list of ZenML integrations that need to be installed for the stack to be usable.'), 'locations': FieldInfo(annotation=Dict[str, str], required=True, title='The locations where the stack can be deployed.', description='The locations where the stack can be deployed, as a dictionary mapping location names to descriptions.'), 'permissions': FieldInfo(annotation=Dict[str, List[str]], required=True, title='The permissions granted to ZenML to access the cloud resources.', description='The permissions granted to ZenML to access the cloud resources, as a dictionary grouping permissions by resource.'), 'post_deploy_instructions': FieldInfo(annotation=str, required=True, title='The instructions for post-deployment.', description='The instructions for post-deployment.'), 'provider': FieldInfo(annotation=StackDeploymentProvider, required=True, title='The provider of the stack deployment.'), 'skypilot_default_regions': FieldInfo(annotation=Dict[str, str], required=True, title='The locations where the Skypilot clusters can be deployed by default.', description='The locations where the Skypilot clusters can be deployed by default, as a dictionary mapping location names to descriptions.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### permissions *: Dict[str, List[str]]*

#### post_deploy_instructions *: str*

#### provider *: [StackDeploymentProvider](zenml.md#zenml.enums.StackDeploymentProvider)*

#### skypilot_default_regions *: Dict[str, str]*

## zenml.models.v2.misc.user_auth module

Model definition for auth users.

### *class* zenml.models.v2.misc.user_auth.UserAuthModel(\*, id: ~uuid.UUID, created: ~datetime.datetime, updated: ~datetime.datetime, active: bool = False, is_service_account: bool, activation_token: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)] | None = None, password: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)] | None = None, name: ~typing.Annotated[str, ~annotated_types.MaxLen(max_length=255)], full_name: ~typing.Annotated[str, ~annotated_types.MaxLen(max_length=255)] = '', email_opted_in: bool | None = None)

Bases: [`BaseZenModel`](zenml.models.v2.base.md#zenml.models.v2.base.base.BaseZenModel)

Authentication Model for the User.

This model is only used server-side. The server endpoints can use this model
to authenticate the user credentials (Token, Password).

#### activation_token *: <lambda>, return_type=PydanticUndefined, when_used=json)] | None*

#### active *: bool*

#### created *: datetime*

#### email_opted_in *: bool | None*

#### full_name *: str*

#### get_hashed_activation_token() → str | None

Returns the hashed activation token, if configured.

Returns:
: The hashed activation token.

#### get_hashed_password() → str | None

Returns the hashed password, if configured.

Returns:
: The hashed password.

#### get_password() → str | None

Get the password.

Returns:
: The password as a plain string, if it exists.

#### id *: UUID*

#### is_service_account *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'activation_token': FieldInfo(annotation=Union[Annotated[SecretStr, PlainSerializer], NoneType], required=False, default=None, exclude=True), 'active': FieldInfo(annotation=bool, required=False, default=False, title='Active account.'), 'created': FieldInfo(annotation=datetime, required=True, title='Time when this resource was created.'), 'email_opted_in': FieldInfo(annotation=Union[bool, NoneType], required=False, default=None, title='Whether the user agreed to share their email. Only relevant for user accounts', description='\`null\` if not answered, \`true\` if agreed, \`false\` if skipped.'), 'full_name': FieldInfo(annotation=str, required=False, default='', title='The full name for the account owner. Only relevant for user accounts.', metadata=[MaxLen(max_length=255)]), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'is_service_account': FieldInfo(annotation=bool, required=True, title='Indicates whether this is a service account or a regular user account.'), 'name': FieldInfo(annotation=str, required=True, title='The unique username for the account.', metadata=[MaxLen(max_length=255)]), 'password': FieldInfo(annotation=Union[Annotated[SecretStr, PlainSerializer], NoneType], required=False, default=None, exclude=True), 'updated': FieldInfo(annotation=datetime, required=True, title='Time when this resource was last updated.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### password *: <lambda>, return_type=PydanticUndefined, when_used=json)] | None*

#### updated *: datetime*

#### *classmethod* verify_activation_token(activation_token: str, user: [UserAuthModel](#zenml.models.v2.misc.user_auth.UserAuthModel) | None = None) → bool

Verifies a given activation token against the stored token.

Args:
: activation_token: Input activation token to be verified.
  user: User for which the activation token is to be verified.

Returns:
: True if the token is valid.

#### *classmethod* verify_password(plain_password: str, user: [UserAuthModel](#zenml.models.v2.misc.user_auth.UserAuthModel) | None = None) → bool

Verifies a given plain password against the stored password.

Args:
: plain_password: Input password to be verified.
  user: User for which the password is to be verified.

Returns:
: True if the passwords match.

## Module contents
