# zenml.integrations.hyperai.service_connectors package

## Submodules

## zenml.integrations.hyperai.service_connectors.hyperai_service_connector module

HyperAI Service Connector.

The HyperAI Service Connector allows authenticating to HyperAI (hyperai.ai)
GPU equipped instances.

### *class* zenml.integrations.hyperai.service_connectors.hyperai_service_connector.HyperAIAuthenticationMethods(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: [`StrEnum`](zenml.utils.md#zenml.utils.enum_utils.StrEnum)

HyperAI Authentication methods.

#### DSA_KEY_OPTIONAL_PASSPHRASE *= 'dsa-key'*

#### ECDSA_KEY_OPTIONAL_PASSPHRASE *= 'ecdsa-key'*

#### ED25519_KEY_OPTIONAL_PASSPHRASE *= 'ed25519-key'*

#### RSA_KEY_OPTIONAL_PASSPHRASE *= 'rsa-key'*

### *class* zenml.integrations.hyperai.service_connectors.hyperai_service_connector.HyperAIConfiguration(\*, base64_ssh_key: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)], ssh_passphrase: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)] | None = None, hostnames: ~typing.List[str], username: str)

Bases: [`HyperAICredentials`](#zenml.integrations.hyperai.service_connectors.hyperai_service_connector.HyperAICredentials)

HyperAI client configuration.

#### hostnames *: List[str]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'base64_ssh_key': FieldInfo(annotation=SecretStr, required=True, title='SSH key (base64)', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')]), 'hostnames': FieldInfo(annotation=List[str], required=True, title='Hostnames of the supported HyperAI instances.'), 'ssh_passphrase': FieldInfo(annotation=Union[Annotated[SecretStr, PlainSerializer], NoneType], required=False, default=None, title='SSH key passphrase'), 'username': FieldInfo(annotation=str, required=True, title='Username to use to connect to the HyperAI instance.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### username *: str*

### *class* zenml.integrations.hyperai.service_connectors.hyperai_service_connector.HyperAICredentials(\*, base64_ssh_key: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)], ssh_passphrase: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)] | None = None)

Bases: [`AuthenticationConfig`](zenml.service_connectors.md#zenml.service_connectors.service_connector.AuthenticationConfig)

HyperAI client authentication credentials.

#### base64_ssh_key *: <lambda>, return_type=PydanticUndefined, when_used=json)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'base64_ssh_key': FieldInfo(annotation=SecretStr, required=True, title='SSH key (base64)', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')]), 'ssh_passphrase': FieldInfo(annotation=Union[Annotated[SecretStr, PlainSerializer], NoneType], required=False, default=None, title='SSH key passphrase')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### ssh_passphrase *: <lambda>, return_type=PydanticUndefined, when_used=json)] | None*

### *class* zenml.integrations.hyperai.service_connectors.hyperai_service_connector.HyperAIServiceConnector(\*, id: UUID | None = None, name: str | None = None, auth_method: str, resource_type: str | None = None, resource_id: str | None = None, expires_at: datetime | None = None, expires_skew_tolerance: int | None = None, expiration_seconds: int | None = None, config: [HyperAIConfiguration](#zenml.integrations.hyperai.service_connectors.hyperai_service_connector.HyperAIConfiguration), allow_implicit_auth_methods: bool = False)

Bases: [`ServiceConnector`](zenml.service_connectors.md#zenml.service_connectors.service_connector.ServiceConnector)

HyperAI service connector.

#### config *: [HyperAIConfiguration](#zenml.integrations.hyperai.service_connectors.hyperai_service_connector.HyperAIConfiguration)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'allow_implicit_auth_methods': FieldInfo(annotation=bool, required=False, default=False), 'auth_method': FieldInfo(annotation=str, required=True), 'config': FieldInfo(annotation=HyperAIConfiguration, required=True), 'expiration_seconds': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'expires_at': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'expires_skew_tolerance': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'resource_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'resource_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## Module contents

HyperAI Service Connector.

### *class* zenml.integrations.hyperai.service_connectors.HyperAIServiceConnector(\*, id: UUID | None = None, name: str | None = None, auth_method: str, resource_type: str | None = None, resource_id: str | None = None, expires_at: datetime | None = None, expires_skew_tolerance: int | None = None, expiration_seconds: int | None = None, config: [HyperAIConfiguration](#zenml.integrations.hyperai.service_connectors.hyperai_service_connector.HyperAIConfiguration), allow_implicit_auth_methods: bool = False)

Bases: [`ServiceConnector`](zenml.service_connectors.md#zenml.service_connectors.service_connector.ServiceConnector)

HyperAI service connector.

#### allow_implicit_auth_methods *: bool*

#### auth_method *: str*

#### config *: [HyperAIConfiguration](#zenml.integrations.hyperai.service_connectors.hyperai_service_connector.HyperAIConfiguration)*

#### expiration_seconds *: int | None*

#### expires_at *: datetime | None*

#### expires_skew_tolerance *: int | None*

#### id *: UUID | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'allow_implicit_auth_methods': FieldInfo(annotation=bool, required=False, default=False), 'auth_method': FieldInfo(annotation=str, required=True), 'config': FieldInfo(annotation=HyperAIConfiguration, required=True), 'expiration_seconds': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'expires_at': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'expires_skew_tolerance': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'resource_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'resource_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

#### resource_id *: str | None*

#### resource_type *: str | None*
