# zenml.integrations.kubernetes.service_connectors package

## Submodules

## zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector module

Kubernetes Service Connector.

The Kubernetes Service Connector implements various authentication methods for
Kubernetes clusters.

### *class* zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesAuthenticationMethods(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: [`StrEnum`](zenml.utils.md#zenml.utils.enum_utils.StrEnum)

Kubernetes Authentication methods.

#### PASSWORD *= 'password'*

#### TOKEN *= 'token'*

### *class* zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesBaseConfig(\*, certificate_authority: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)] | None = None, server: str, insecure: bool = False, cluster_name: str)

Bases: [`KubernetesServerConfig`](#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesServerConfig)

Kubernetes basic config.

#### cluster_name *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'certificate_authority': FieldInfo(annotation=Union[Annotated[SecretStr, PlainSerializer], NoneType], required=False, default=None, title='Kubernetes CA Certificate (base64 encoded)'), 'cluster_name': FieldInfo(annotation=str, required=True, title='Kubernetes cluster name to be used in the kubeconfig file'), 'insecure': FieldInfo(annotation=bool, required=False, default=False, title='Skip TLS verification for the server certificate'), 'server': FieldInfo(annotation=str, required=True, title='Kubernetes Server URL')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesServerConfig(\*, certificate_authority: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)] | None = None, server: str, insecure: bool = False)

Bases: [`KubernetesServerCredentials`](#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesServerCredentials)

Kubernetes server config.

#### insecure *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'certificate_authority': FieldInfo(annotation=Union[Annotated[SecretStr, PlainSerializer], NoneType], required=False, default=None, title='Kubernetes CA Certificate (base64 encoded)'), 'insecure': FieldInfo(annotation=bool, required=False, default=False, title='Skip TLS verification for the server certificate'), 'server': FieldInfo(annotation=str, required=True, title='Kubernetes Server URL')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### server *: str*

### *class* zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesServerCredentials(\*, certificate_authority: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)] | None = None)

Bases: [`AuthenticationConfig`](zenml.service_connectors.md#zenml.service_connectors.service_connector.AuthenticationConfig)

Kubernetes server authentication config.

#### certificate_authority *: <lambda>, return_type=PydanticUndefined, when_used=json)] | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'certificate_authority': FieldInfo(annotation=Union[Annotated[SecretStr, PlainSerializer], NoneType], required=False, default=None, title='Kubernetes CA Certificate (base64 encoded)')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesServiceConnector(\*, id: UUID | None = None, name: str | None = None, auth_method: str, resource_type: str | None = None, resource_id: str | None = None, expires_at: datetime | None = None, expires_skew_tolerance: int | None = None, expiration_seconds: int | None = None, config: [KubernetesBaseConfig](#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesBaseConfig), allow_implicit_auth_methods: bool = False)

Bases: [`ServiceConnector`](zenml.service_connectors.md#zenml.service_connectors.service_connector.ServiceConnector)

Kubernetes service connector.

#### config *: [KubernetesBaseConfig](#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesBaseConfig)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'allow_implicit_auth_methods': FieldInfo(annotation=bool, required=False, default=False), 'auth_method': FieldInfo(annotation=str, required=True), 'config': FieldInfo(annotation=KubernetesBaseConfig, required=True), 'expiration_seconds': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'expires_at': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'expires_skew_tolerance': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'resource_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'resource_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesTokenConfig(\*, client_certificate: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)] | None = None, client_key: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)] | None = None, token: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)] | None = None, certificate_authority: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)] | None = None, server: str, insecure: bool = False, cluster_name: str)

Bases: [`KubernetesBaseConfig`](#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesBaseConfig), [`KubernetesTokenCredentials`](#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesTokenCredentials)

Kubernetes token config.

#### certificate_authority *: PlainSerializedSecretStr | None*

#### cluster_name *: str*

#### insecure *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'certificate_authority': FieldInfo(annotation=Union[Annotated[SecretStr, PlainSerializer], NoneType], required=False, default=None, title='Kubernetes CA Certificate (base64 encoded)'), 'client_certificate': FieldInfo(annotation=Union[Annotated[SecretStr, PlainSerializer], NoneType], required=False, default=None, title='Kubernetes Client Certificate (base64 encoded)'), 'client_key': FieldInfo(annotation=Union[Annotated[SecretStr, PlainSerializer], NoneType], required=False, default=None, title='Kubernetes Client Key (base64 encoded)'), 'cluster_name': FieldInfo(annotation=str, required=True, title='Kubernetes cluster name to be used in the kubeconfig file'), 'insecure': FieldInfo(annotation=bool, required=False, default=False, title='Skip TLS verification for the server certificate'), 'server': FieldInfo(annotation=str, required=True, title='Kubernetes Server URL'), 'token': FieldInfo(annotation=Union[Annotated[SecretStr, PlainSerializer], NoneType], required=False, default=None, title='Kubernetes Token')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### server *: str*

### *class* zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesTokenCredentials(\*, client_certificate: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)] | None = None, client_key: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)] | None = None, token: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)] | None = None)

Bases: [`AuthenticationConfig`](zenml.service_connectors.md#zenml.service_connectors.service_connector.AuthenticationConfig)

Kubernetes token authentication config.

#### client_certificate *: <lambda>, return_type=PydanticUndefined, when_used=json)] | None*

#### client_key *: <lambda>, return_type=PydanticUndefined, when_used=json)] | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'client_certificate': FieldInfo(annotation=Union[Annotated[SecretStr, PlainSerializer], NoneType], required=False, default=None, title='Kubernetes Client Certificate (base64 encoded)'), 'client_key': FieldInfo(annotation=Union[Annotated[SecretStr, PlainSerializer], NoneType], required=False, default=None, title='Kubernetes Client Key (base64 encoded)'), 'token': FieldInfo(annotation=Union[Annotated[SecretStr, PlainSerializer], NoneType], required=False, default=None, title='Kubernetes Token')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### token *: <lambda>, return_type=PydanticUndefined, when_used=json)] | None*

### *class* zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesUserPasswordConfig(\*, username: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)], password: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)], certificate_authority: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)] | None = None, server: str, insecure: bool = False, cluster_name: str)

Bases: [`KubernetesBaseConfig`](#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesBaseConfig), [`KubernetesUserPasswordCredentials`](#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesUserPasswordCredentials)

Kubernetes user/pass config.

#### certificate_authority *: PlainSerializedSecretStr | None*

#### cluster_name *: str*

#### insecure *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'certificate_authority': FieldInfo(annotation=Union[Annotated[SecretStr, PlainSerializer], NoneType], required=False, default=None, title='Kubernetes CA Certificate (base64 encoded)'), 'cluster_name': FieldInfo(annotation=str, required=True, title='Kubernetes cluster name to be used in the kubeconfig file'), 'insecure': FieldInfo(annotation=bool, required=False, default=False, title='Skip TLS verification for the server certificate'), 'password': FieldInfo(annotation=SecretStr, required=True, title='Kubernetes Password', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')]), 'server': FieldInfo(annotation=str, required=True, title='Kubernetes Server URL'), 'username': FieldInfo(annotation=SecretStr, required=True, title='Kubernetes Username', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### server *: str*

### *class* zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesUserPasswordCredentials(\*, username: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)], password: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)])

Bases: [`AuthenticationConfig`](zenml.service_connectors.md#zenml.service_connectors.service_connector.AuthenticationConfig)

Kubernetes user/pass authentication config.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'password': FieldInfo(annotation=SecretStr, required=True, title='Kubernetes Password', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')]), 'username': FieldInfo(annotation=SecretStr, required=True, title='Kubernetes Username', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### password *: <lambda>, return_type=PydanticUndefined, when_used=json)]*

#### username *: <lambda>, return_type=PydanticUndefined, when_used=json)]*

## Module contents

Kubernetes Service Connector.

### *class* zenml.integrations.kubernetes.service_connectors.KubernetesServiceConnector(\*, id: UUID | None = None, name: str | None = None, auth_method: str, resource_type: str | None = None, resource_id: str | None = None, expires_at: datetime | None = None, expires_skew_tolerance: int | None = None, expiration_seconds: int | None = None, config: [KubernetesBaseConfig](#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesBaseConfig), allow_implicit_auth_methods: bool = False)

Bases: [`ServiceConnector`](zenml.service_connectors.md#zenml.service_connectors.service_connector.ServiceConnector)

Kubernetes service connector.

#### allow_implicit_auth_methods *: bool*

#### auth_method *: str*

#### config *: [KubernetesBaseConfig](#zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector.KubernetesBaseConfig)*

#### expiration_seconds *: int | None*

#### expires_at *: datetime | None*

#### expires_skew_tolerance *: int | None*

#### id *: UUID | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'allow_implicit_auth_methods': FieldInfo(annotation=bool, required=False, default=False), 'auth_method': FieldInfo(annotation=str, required=True), 'config': FieldInfo(annotation=KubernetesBaseConfig, required=True), 'expiration_seconds': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'expires_at': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'expires_skew_tolerance': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'resource_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'resource_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

#### resource_id *: str | None*

#### resource_type *: str | None*
