# zenml.integrations.azure.service_connectors package

## Submodules

## zenml.integrations.azure.service_connectors.azure_service_connector module

Azure Service Connector.

### *class* zenml.integrations.azure.service_connectors.azure_service_connector.AzureAccessToken(\*, token: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)])

Bases: [`AuthenticationConfig`](zenml.service_connectors.md#zenml.service_connectors.service_connector.AuthenticationConfig)

Azure access token credentials.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'token': FieldInfo(annotation=SecretStr, required=True, title='Azure Access Token', description='The Azure access token to use for authentication', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### token *: <lambda>, return_type=PydanticUndefined, when_used=json)]*

### *class* zenml.integrations.azure.service_connectors.azure_service_connector.AzureAccessTokenConfig(\*, token: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)], subscription_id: ~uuid.UUID | None = None, tenant_id: ~uuid.UUID | None = None, resource_group: str | None = None, storage_account: str | None = None)

Bases: [`AzureBaseConfig`](#zenml.integrations.azure.service_connectors.azure_service_connector.AzureBaseConfig), [`AzureAccessToken`](#zenml.integrations.azure.service_connectors.azure_service_connector.AzureAccessToken)

Azure token configuration.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'resource_group': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Azure Resource Group', description='A resource group may be used to restrict the scope of Azure resources like AKS clusters and ACR repositories. If not specified, ZenML will retrieve resources from all resource groups accessible with the configured credentials.'), 'storage_account': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Azure Storage Account', description='The name of an Azure storage account may be used to restrict the scope of Azure Blob storage containers. If not specified, ZenML will retrieve blob containers from all storage accounts accessible with the configured credentials.'), 'subscription_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='Azure Subscription ID', description='The subscription ID of the Azure account. If not specified, ZenML will attempt to retrieve the subscription ID from Azure using the configured credentials.'), 'tenant_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='Azure Tenant ID', description='The tenant ID of the Azure account. If not specified, ZenML will attempt to retrieve the tenant from Azure using the configured credentials.'), 'token': FieldInfo(annotation=SecretStr, required=True, title='Azure Access Token', description='The Azure access token to use for authentication', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### resource_group *: str | None*

#### storage_account *: str | None*

#### subscription_id *: UUID | None*

#### tenant_id *: UUID | None*

### *class* zenml.integrations.azure.service_connectors.azure_service_connector.AzureAuthenticationMethods(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: [`StrEnum`](zenml.utils.md#zenml.utils.enum_utils.StrEnum)

Azure Authentication methods.

#### ACCESS_TOKEN *= 'access-token'*

#### IMPLICIT *= 'implicit'*

#### SERVICE_PRINCIPAL *= 'service-principal'*

### *class* zenml.integrations.azure.service_connectors.azure_service_connector.AzureBaseConfig(\*, subscription_id: UUID | None = None, tenant_id: UUID | None = None, resource_group: str | None = None, storage_account: str | None = None)

Bases: [`AuthenticationConfig`](zenml.service_connectors.md#zenml.service_connectors.service_connector.AuthenticationConfig)

Azure base configuration.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'resource_group': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Azure Resource Group', description='A resource group may be used to restrict the scope of Azure resources like AKS clusters and ACR repositories. If not specified, ZenML will retrieve resources from all resource groups accessible with the configured credentials.'), 'storage_account': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Azure Storage Account', description='The name of an Azure storage account may be used to restrict the scope of Azure Blob storage containers. If not specified, ZenML will retrieve blob containers from all storage accounts accessible with the configured credentials.'), 'subscription_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='Azure Subscription ID', description='The subscription ID of the Azure account. If not specified, ZenML will attempt to retrieve the subscription ID from Azure using the configured credentials.'), 'tenant_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='Azure Tenant ID', description='The tenant ID of the Azure account. If not specified, ZenML will attempt to retrieve the tenant from Azure using the configured credentials.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### resource_group *: str | None*

#### storage_account *: str | None*

#### subscription_id *: UUID | None*

#### tenant_id *: UUID | None*

### *class* zenml.integrations.azure.service_connectors.azure_service_connector.AzureClientConfig(\*, subscription_id: UUID | None = None, tenant_id: UUID, resource_group: str | None = None, storage_account: str | None = None, client_id: UUID)

Bases: [`AzureBaseConfig`](#zenml.integrations.azure.service_connectors.azure_service_connector.AzureBaseConfig)

Azure client configuration.

#### client_id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'client_id': FieldInfo(annotation=UUID, required=True, title='Azure Client ID', description="The service principal's client ID"), 'resource_group': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Azure Resource Group', description='A resource group may be used to restrict the scope of Azure resources like AKS clusters and ACR repositories. If not specified, ZenML will retrieve resources from all resource groups accessible with the configured credentials.'), 'storage_account': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Azure Storage Account', description='The name of an Azure storage account may be used to restrict the scope of Azure Blob storage containers. If not specified, ZenML will retrieve blob containers from all storage accounts accessible with the configured credentials.'), 'subscription_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='Azure Subscription ID', description='The subscription ID of the Azure account. If not specified, ZenML will attempt to retrieve the subscription ID from Azure using the configured credentials.'), 'tenant_id': FieldInfo(annotation=UUID, required=True, title='Azure Tenant ID', description="ID of the service principal's tenant. Also called its 'directory' ID.")}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### tenant_id *: UUID*

### *class* zenml.integrations.azure.service_connectors.azure_service_connector.AzureClientSecret(\*, client_secret: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)])

Bases: [`AuthenticationConfig`](zenml.service_connectors.md#zenml.service_connectors.service_connector.AuthenticationConfig)

Azure client secret credentials.

#### client_secret *: <lambda>, return_type=PydanticUndefined, when_used=json)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'client_secret': FieldInfo(annotation=SecretStr, required=True, title='Service principal client secret', description='The client secret of the service principal', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.integrations.azure.service_connectors.azure_service_connector.AzureServiceConnector(\*, id: UUID | None = None, name: str | None = None, auth_method: str, resource_type: str | None = None, resource_id: str | None = None, expires_at: datetime | None = None, expires_skew_tolerance: int | None = None, expiration_seconds: int | None = None, config: [AzureBaseConfig](#zenml.integrations.azure.service_connectors.azure_service_connector.AzureBaseConfig), allow_implicit_auth_methods: bool = False)

Bases: [`ServiceConnector`](zenml.service_connectors.md#zenml.service_connectors.service_connector.ServiceConnector)

Azure service connector.

#### config *: [AzureBaseConfig](#zenml.integrations.azure.service_connectors.azure_service_connector.AzureBaseConfig)*

#### get_azure_credential(auth_method: str, resource_type: str | None = None, resource_id: str | None = None) → Tuple[TokenCredential, datetime | None]

Get an Azure credential for the specified resource.

Args:
: auth_method: The authentication method to use.
  resource_type: The resource type to get a credential for.
  resource_id: The resource ID to get a credential for.

Returns:
: An Azure credential for the specified resource and its expiration
  timestamp, if applicable.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'allow_implicit_auth_methods': FieldInfo(annotation=bool, required=False, default=False), 'auth_method': FieldInfo(annotation=str, required=True), 'config': FieldInfo(annotation=AzureBaseConfig, required=True), 'expiration_seconds': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'expires_at': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'expires_skew_tolerance': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'resource_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'resource_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

This function is meant to behave like a BaseModel method to initialise private attributes.

It takes context as an argument since that’s what pydantic-core passes when calling it.

Args:
: self: The BaseModel instance.
  context: The context.

#### *property* subscription *: Tuple[str, str]*

Get the Azure subscription ID and name.

Returns:
: The Azure subscription ID and name.

Raises:
: AuthorizationException: If the Azure subscription could not be
  : determined or doesn’t match the configured subscription ID.

#### *property* tenant_id *: str*

Get the Azure tenant ID.

Returns:
: The Azure tenant ID.

Raises:
: AuthorizationException: If the Azure tenant ID could not be
  : determined or doesn’t match the configured tenant ID.

### *class* zenml.integrations.azure.service_connectors.azure_service_connector.AzureServicePrincipalConfig(\*, client_secret: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)], subscription_id: ~uuid.UUID | None = None, tenant_id: ~uuid.UUID, resource_group: str | None = None, storage_account: str | None = None, client_id: ~uuid.UUID)

Bases: [`AzureClientConfig`](#zenml.integrations.azure.service_connectors.azure_service_connector.AzureClientConfig), [`AzureClientSecret`](#zenml.integrations.azure.service_connectors.azure_service_connector.AzureClientSecret)

Azure service principal configuration.

#### client_id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'client_id': FieldInfo(annotation=UUID, required=True, title='Azure Client ID', description="The service principal's client ID"), 'client_secret': FieldInfo(annotation=SecretStr, required=True, title='Service principal client secret', description='The client secret of the service principal', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')]), 'resource_group': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Azure Resource Group', description='A resource group may be used to restrict the scope of Azure resources like AKS clusters and ACR repositories. If not specified, ZenML will retrieve resources from all resource groups accessible with the configured credentials.'), 'storage_account': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Azure Storage Account', description='The name of an Azure storage account may be used to restrict the scope of Azure Blob storage containers. If not specified, ZenML will retrieve blob containers from all storage accounts accessible with the configured credentials.'), 'subscription_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, title='Azure Subscription ID', description='The subscription ID of the Azure account. If not specified, ZenML will attempt to retrieve the subscription ID from Azure using the configured credentials.'), 'tenant_id': FieldInfo(annotation=UUID, required=True, title='Azure Tenant ID', description="ID of the service principal's tenant. Also called its 'directory' ID.")}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### resource_group *: str | None*

#### storage_account *: str | None*

#### subscription_id *: UUID | None*

#### tenant_id *: UUID*

### *class* zenml.integrations.azure.service_connectors.azure_service_connector.ZenMLAzureTokenCredential(token: str, expires_at: datetime)

Bases: `TokenCredential`

ZenML Azure token credential.

This class is used to provide a pre-configured token credential to Azure
clients. Tokens are generated from other Azure credentials and are served
to Azure clients to authenticate requests.

#### get_token(\*scopes: str, \*\*kwargs: Any) → Any

Get token.

Args:
: ```
  *
  ```
  <br/>
  scopes: Scopes
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments

Returns:
: Token

## Module contents

Azure Service Connector.

### *class* zenml.integrations.azure.service_connectors.AzureServiceConnector(\*, id: UUID | None = None, name: str | None = None, auth_method: str, resource_type: str | None = None, resource_id: str | None = None, expires_at: datetime | None = None, expires_skew_tolerance: int | None = None, expiration_seconds: int | None = None, config: [AzureBaseConfig](#zenml.integrations.azure.service_connectors.azure_service_connector.AzureBaseConfig), allow_implicit_auth_methods: bool = False)

Bases: [`ServiceConnector`](zenml.service_connectors.md#zenml.service_connectors.service_connector.ServiceConnector)

Azure service connector.

#### allow_implicit_auth_methods *: bool*

#### auth_method *: str*

#### config *: [AzureBaseConfig](#zenml.integrations.azure.service_connectors.azure_service_connector.AzureBaseConfig)*

#### expiration_seconds *: int | None*

#### expires_at *: datetime | None*

#### expires_skew_tolerance *: int | None*

#### get_azure_credential(auth_method: str, resource_type: str | None = None, resource_id: str | None = None) → Tuple[TokenCredential, datetime | None]

Get an Azure credential for the specified resource.

Args:
: auth_method: The authentication method to use.
  resource_type: The resource type to get a credential for.
  resource_id: The resource ID to get a credential for.

Returns:
: An Azure credential for the specified resource and its expiration
  timestamp, if applicable.

#### id *: UUID | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'allow_implicit_auth_methods': FieldInfo(annotation=bool, required=False, default=False), 'auth_method': FieldInfo(annotation=str, required=True), 'config': FieldInfo(annotation=AzureBaseConfig, required=True), 'expiration_seconds': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'expires_at': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'expires_skew_tolerance': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'resource_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'resource_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

This function is meant to behave like a BaseModel method to initialise private attributes.

It takes context as an argument since that’s what pydantic-core passes when calling it.

Args:
: self: The BaseModel instance.
  context: The context.

#### name *: str | None*

#### resource_id *: str | None*

#### resource_type *: str | None*

#### *property* subscription *: Tuple[str, str]*

Get the Azure subscription ID and name.

Returns:
: The Azure subscription ID and name.

Raises:
: AuthorizationException: If the Azure subscription could not be
  : determined or doesn’t match the configured subscription ID.

#### *property* tenant_id *: str*

Get the Azure tenant ID.

Returns:
: The Azure tenant ID.

Raises:
: AuthorizationException: If the Azure tenant ID could not be
  : determined or doesn’t match the configured tenant ID.
