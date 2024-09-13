# zenml.integrations.aws.service_connectors package

## Submodules

## zenml.integrations.aws.service_connectors.aws_service_connector module

AWS Service Connector.

The AWS Service Connector implements various authentication methods for AWS
services:

- Explicit AWS secret key (access key, secret key)
- Explicit  AWS STS tokens (access key, secret key, session token)
- IAM roles (i.e. generating temporary STS tokens on the fly by assuming an

IAM role)
- IAM user federation tokens
- STS Session tokens

### *class* zenml.integrations.aws.service_connectors.aws_service_connector.AWSAuthenticationMethods(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: [`StrEnum`](zenml.utils.md#zenml.utils.enum_utils.StrEnum)

AWS Authentication methods.

#### FEDERATION_TOKEN *= 'federation-token'*

#### IAM_ROLE *= 'iam-role'*

#### IMPLICIT *= 'implicit'*

#### SECRET_KEY *= 'secret-key'*

#### SESSION_TOKEN *= 'session-token'*

#### STS_TOKEN *= 'sts-token'*

### *class* zenml.integrations.aws.service_connectors.aws_service_connector.AWSBaseConfig(\*, region: str, endpoint_url: str | None = None)

Bases: [`AuthenticationConfig`](zenml.service_connectors.md#zenml.service_connectors.service_connector.AuthenticationConfig)

AWS base configuration.

#### endpoint_url *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'endpoint_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='AWS Endpoint URL'), 'region': FieldInfo(annotation=str, required=True, title='AWS Region')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### region *: str*

### *class* zenml.integrations.aws.service_connectors.aws_service_connector.AWSImplicitConfig(\*, policy_arns: List[str] | None = None, policy: str | None = None, region: str, endpoint_url: str | None = None, profile_name: str | None = None, role_arn: str | None = None)

Bases: [`AWSBaseConfig`](#zenml.integrations.aws.service_connectors.aws_service_connector.AWSBaseConfig), [`AWSSessionPolicy`](#zenml.integrations.aws.service_connectors.aws_service_connector.AWSSessionPolicy)

AWS implicit configuration.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'endpoint_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='AWS Endpoint URL'), 'policy': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='An IAM policy in JSON format that you want to use as an inline session policy'), 'policy_arns': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None, title='ARNs of the IAM managed policies that you want to use as a managed session policy. The policies must exist in the same account as the IAM user that is requesting temporary credentials.'), 'profile_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='AWS Profile Name'), 'region': FieldInfo(annotation=str, required=True, title='AWS Region'), 'role_arn': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='Optional AWS IAM Role ARN to assume')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### profile_name *: str | None*

#### role_arn *: str | None*

### *class* zenml.integrations.aws.service_connectors.aws_service_connector.AWSSecretKey(\*, aws_access_key_id: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)], aws_secret_access_key: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)])

Bases: [`AuthenticationConfig`](zenml.service_connectors.md#zenml.service_connectors.service_connector.AuthenticationConfig)

AWS secret key credentials.

#### aws_access_key_id *: <lambda>, return_type=PydanticUndefined, when_used=json)]*

#### aws_secret_access_key *: <lambda>, return_type=PydanticUndefined, when_used=json)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'aws_access_key_id': FieldInfo(annotation=SecretStr, required=True, title='AWS Access Key ID', description='An AWS access key ID associated with an AWS account or IAM user.', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')]), 'aws_secret_access_key': FieldInfo(annotation=SecretStr, required=True, title='AWS Secret Access Key', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.integrations.aws.service_connectors.aws_service_connector.AWSSecretKeyConfig(\*, aws_access_key_id: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)], aws_secret_access_key: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)], region: str, endpoint_url: str | None = None)

Bases: [`AWSBaseConfig`](#zenml.integrations.aws.service_connectors.aws_service_connector.AWSBaseConfig), [`AWSSecretKey`](#zenml.integrations.aws.service_connectors.aws_service_connector.AWSSecretKey)

AWS secret key authentication configuration.

#### endpoint_url *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'aws_access_key_id': FieldInfo(annotation=SecretStr, required=True, title='AWS Access Key ID', description='An AWS access key ID associated with an AWS account or IAM user.', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')]), 'aws_secret_access_key': FieldInfo(annotation=SecretStr, required=True, title='AWS Secret Access Key', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')]), 'endpoint_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='AWS Endpoint URL'), 'region': FieldInfo(annotation=str, required=True, title='AWS Region')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### region *: str*

### *class* zenml.integrations.aws.service_connectors.aws_service_connector.AWSServiceConnector(\*, id: UUID | None = None, name: str | None = None, auth_method: str, resource_type: str | None = None, resource_id: str | None = None, expires_at: datetime | None = None, expires_skew_tolerance: int | None = None, expiration_seconds: int | None = None, config: [AWSBaseConfig](#zenml.integrations.aws.service_connectors.aws_service_connector.AWSBaseConfig), allow_implicit_auth_methods: bool = False)

Bases: [`ServiceConnector`](zenml.service_connectors.md#zenml.service_connectors.service_connector.ServiceConnector)

AWS service connector.

#### *property* account_id *: str*

Get the AWS account ID.

Returns:
: The AWS account ID.

Raises:
: AuthorizationException: If the AWS account ID could not be
  : determined.

#### config *: [AWSBaseConfig](#zenml.integrations.aws.service_connectors.aws_service_connector.AWSBaseConfig)*

#### get_boto3_session(auth_method: str, resource_type: str | None = None, resource_id: str | None = None) → Tuple[Session, datetime | None]

Get a boto3 session for the specified resource.

Args:
: auth_method: The authentication method to use.
  resource_type: The resource type to get a boto3 session for.
  resource_id: The resource ID to get a boto3 session for.

Returns:
: A boto3 session for the specified resource and its expiration
  timestamp, if applicable.

#### get_ecr_client() → BaseClient

Get an ECR client.

Raises:
: ValueError: If the service connector is not able to instantiate an
  : ECR client.

Returns:
: An ECR client.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'allow_implicit_auth_methods': FieldInfo(annotation=bool, required=False, default=False), 'auth_method': FieldInfo(annotation=str, required=True), 'config': FieldInfo(annotation=AWSBaseConfig, required=True), 'expiration_seconds': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'expires_at': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'expires_skew_tolerance': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'resource_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'resource_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

This function is meant to behave like a BaseModel method to initialise private attributes.

It takes context as an argument since that’s what pydantic-core passes when calling it.

Args:
: self: The BaseModel instance.
  context: The context.

### *class* zenml.integrations.aws.service_connectors.aws_service_connector.AWSSessionPolicy(\*, policy_arns: List[str] | None = None, policy: str | None = None)

Bases: [`AuthenticationConfig`](zenml.service_connectors.md#zenml.service_connectors.service_connector.AuthenticationConfig)

AWS session IAM policy configuration.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'policy': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='An IAM policy in JSON format that you want to use as an inline session policy'), 'policy_arns': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None, title='ARNs of the IAM managed policies that you want to use as a managed session policy. The policies must exist in the same account as the IAM user that is requesting temporary credentials.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### policy *: str | None*

#### policy_arns *: List[str] | None*

### *class* zenml.integrations.aws.service_connectors.aws_service_connector.FederationTokenAuthenticationConfig(\*, policy_arns: ~typing.List[str] | None = None, policy: str | None = None, aws_access_key_id: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)], aws_secret_access_key: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)], region: str, endpoint_url: str | None = None)

Bases: [`AWSSecretKeyConfig`](#zenml.integrations.aws.service_connectors.aws_service_connector.AWSSecretKeyConfig), [`AWSSessionPolicy`](#zenml.integrations.aws.service_connectors.aws_service_connector.AWSSessionPolicy)

AWS federation token authentication config.

#### aws_access_key_id *: PlainSerializedSecretStr*

#### aws_secret_access_key *: PlainSerializedSecretStr*

#### endpoint_url *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'aws_access_key_id': FieldInfo(annotation=SecretStr, required=True, title='AWS Access Key ID', description='An AWS access key ID associated with an AWS account or IAM user.', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')]), 'aws_secret_access_key': FieldInfo(annotation=SecretStr, required=True, title='AWS Secret Access Key', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')]), 'endpoint_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='AWS Endpoint URL'), 'policy': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='An IAM policy in JSON format that you want to use as an inline session policy'), 'policy_arns': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None, title='ARNs of the IAM managed policies that you want to use as a managed session policy. The policies must exist in the same account as the IAM user that is requesting temporary credentials.'), 'region': FieldInfo(annotation=str, required=True, title='AWS Region')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### region *: str*

### *class* zenml.integrations.aws.service_connectors.aws_service_connector.IAMRoleAuthenticationConfig(\*, policy_arns: ~typing.List[str] | None = None, policy: str | None = None, aws_access_key_id: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)], aws_secret_access_key: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)], region: str, endpoint_url: str | None = None, role_arn: str)

Bases: [`AWSSecretKeyConfig`](#zenml.integrations.aws.service_connectors.aws_service_connector.AWSSecretKeyConfig), [`AWSSessionPolicy`](#zenml.integrations.aws.service_connectors.aws_service_connector.AWSSessionPolicy)

AWS IAM authentication config.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'aws_access_key_id': FieldInfo(annotation=SecretStr, required=True, title='AWS Access Key ID', description='An AWS access key ID associated with an AWS account or IAM user.', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')]), 'aws_secret_access_key': FieldInfo(annotation=SecretStr, required=True, title='AWS Secret Access Key', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')]), 'endpoint_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='AWS Endpoint URL'), 'policy': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='An IAM policy in JSON format that you want to use as an inline session policy'), 'policy_arns': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None, title='ARNs of the IAM managed policies that you want to use as a managed session policy. The policies must exist in the same account as the IAM user that is requesting temporary credentials.'), 'region': FieldInfo(annotation=str, required=True, title='AWS Region'), 'role_arn': FieldInfo(annotation=str, required=True, title='AWS IAM Role ARN')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### role_arn *: str*

### *class* zenml.integrations.aws.service_connectors.aws_service_connector.STSToken(\*, aws_access_key_id: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)], aws_secret_access_key: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)], aws_session_token: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)])

Bases: [`AWSSecretKey`](#zenml.integrations.aws.service_connectors.aws_service_connector.AWSSecretKey)

AWS STS token.

#### aws_session_token *: <lambda>, return_type=PydanticUndefined, when_used=json)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'aws_access_key_id': FieldInfo(annotation=SecretStr, required=True, title='AWS Access Key ID', description='An AWS access key ID associated with an AWS account or IAM user.', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')]), 'aws_secret_access_key': FieldInfo(annotation=SecretStr, required=True, title='AWS Secret Access Key', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')]), 'aws_session_token': FieldInfo(annotation=SecretStr, required=True, title='AWS Session Token', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.integrations.aws.service_connectors.aws_service_connector.STSTokenConfig(\*, aws_access_key_id: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)], aws_secret_access_key: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)], aws_session_token: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)], region: str, endpoint_url: str | None = None)

Bases: [`AWSBaseConfig`](#zenml.integrations.aws.service_connectors.aws_service_connector.AWSBaseConfig), [`STSToken`](#zenml.integrations.aws.service_connectors.aws_service_connector.STSToken)

AWS STS token authentication configuration.

#### endpoint_url *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'aws_access_key_id': FieldInfo(annotation=SecretStr, required=True, title='AWS Access Key ID', description='An AWS access key ID associated with an AWS account or IAM user.', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')]), 'aws_secret_access_key': FieldInfo(annotation=SecretStr, required=True, title='AWS Secret Access Key', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')]), 'aws_session_token': FieldInfo(annotation=SecretStr, required=True, title='AWS Session Token', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')]), 'endpoint_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='AWS Endpoint URL'), 'region': FieldInfo(annotation=str, required=True, title='AWS Region')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### region *: str*

### *class* zenml.integrations.aws.service_connectors.aws_service_connector.SessionTokenAuthenticationConfig(\*, aws_access_key_id: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)], aws_secret_access_key: ~pydantic.types.Annotated[~pydantic.types.SecretStr, ~pydantic.functional_serializers.PlainSerializer(func=~zenml.utils.secret_utils.<lambda>, return_type=PydanticUndefined, when_used=json)], region: str, endpoint_url: str | None = None)

Bases: [`AWSSecretKeyConfig`](#zenml.integrations.aws.service_connectors.aws_service_connector.AWSSecretKeyConfig)

AWS session token authentication config.

#### aws_access_key_id *: PlainSerializedSecretStr*

#### aws_secret_access_key *: PlainSerializedSecretStr*

#### endpoint_url *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'aws_access_key_id': FieldInfo(annotation=SecretStr, required=True, title='AWS Access Key ID', description='An AWS access key ID associated with an AWS account or IAM user.', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')]), 'aws_secret_access_key': FieldInfo(annotation=SecretStr, required=True, title='AWS Secret Access Key', metadata=[PlainSerializer(func=<function <lambda>>, return_type=PydanticUndefined, when_used='json')]), 'endpoint_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, title='AWS Endpoint URL'), 'region': FieldInfo(annotation=str, required=True, title='AWS Region')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### region *: str*

## Module contents

AWS Service Connector.

### *class* zenml.integrations.aws.service_connectors.AWSServiceConnector(\*, id: UUID | None = None, name: str | None = None, auth_method: str, resource_type: str | None = None, resource_id: str | None = None, expires_at: datetime | None = None, expires_skew_tolerance: int | None = None, expiration_seconds: int | None = None, config: [AWSBaseConfig](#zenml.integrations.aws.service_connectors.aws_service_connector.AWSBaseConfig), allow_implicit_auth_methods: bool = False)

Bases: [`ServiceConnector`](zenml.service_connectors.md#zenml.service_connectors.service_connector.ServiceConnector)

AWS service connector.

#### *property* account_id *: str*

Get the AWS account ID.

Returns:
: The AWS account ID.

Raises:
: AuthorizationException: If the AWS account ID could not be
  : determined.

#### allow_implicit_auth_methods *: bool*

#### auth_method *: str*

#### config *: [AWSBaseConfig](#zenml.integrations.aws.service_connectors.aws_service_connector.AWSBaseConfig)*

#### expiration_seconds *: int | None*

#### expires_at *: datetime | None*

#### expires_skew_tolerance *: int | None*

#### get_boto3_session(auth_method: str, resource_type: str | None = None, resource_id: str | None = None) → Tuple[Session, datetime | None]

Get a boto3 session for the specified resource.

Args:
: auth_method: The authentication method to use.
  resource_type: The resource type to get a boto3 session for.
  resource_id: The resource ID to get a boto3 session for.

Returns:
: A boto3 session for the specified resource and its expiration
  timestamp, if applicable.

#### get_ecr_client() → BaseClient

Get an ECR client.

Raises:
: ValueError: If the service connector is not able to instantiate an
  : ECR client.

Returns:
: An ECR client.

#### id *: UUID | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'allow_implicit_auth_methods': FieldInfo(annotation=bool, required=False, default=False), 'auth_method': FieldInfo(annotation=str, required=True), 'config': FieldInfo(annotation=AWSBaseConfig, required=True), 'expiration_seconds': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'expires_at': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'expires_skew_tolerance': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'resource_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'resource_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

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
