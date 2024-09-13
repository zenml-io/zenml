# zenml.integrations.seldon.secret_schemas package

## Submodules

## zenml.integrations.seldon.secret_schemas.secret_schemas module

Implementation for Seldon secret schemas.

### *class* zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonAzureSecretSchema(\*, rclone_config_az_type: Literal['azureblob'] = 'azureblob', rclone_config_az_env_auth: bool = False, rclone_config_az_account: str | None = None, rclone_config_az_key: str | None = None, rclone_config_az_sas_url: str | None = None, rclone_config_az_use_msi: bool = False, rclone_config_az_client_secret: str | None = None, rclone_config_az_client_id: str | None = None, rclone_config_az_tenant: str | None = None)

Bases: [`BaseSecretSchema`](zenml.secret.md#zenml.secret.base_secret.BaseSecretSchema)

Seldon Azure Blob Storage credentials.

Based on: [https://rclone.org/azureblob/](https://rclone.org/azureblob/)

Attributes:
: rclone_config_az_type: the rclone config type. Must be set to
  : “azureblob” for this schema.
  <br/>
  rclone_config_az_env_auth: read credentials from runtime
  : (environment variables or MSI).
  <br/>
  rclone_config_az_account: storage Account Name. Leave blank to
  : use SAS URL or MSI.
  <br/>
  rclone_config_az_key: storage Account Key. Leave blank to
  : use SAS URL or MSI.
  <br/>
  rclone_config_az_sas_url: SAS URL for container level access
  : only. Leave blank if using account/key or MSI.
  <br/>
  rclone_config_az_use_msi: use a managed service identity to
  : authenticate (only works in Azure).
  <br/>
  rclone_config_az_client_secret: client secret for service
  : principal authentication.
  <br/>
  rclone_config_az_client_id: client id for service principal
  : authentication.
  <br/>
  rclone_config_az_tenant: tenant id for service principal
  : authentication.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'rclone_config_az_account': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_az_client_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_az_client_secret': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_az_env_auth': FieldInfo(annotation=bool, required=False, default=False), 'rclone_config_az_key': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_az_sas_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_az_tenant': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_az_type': FieldInfo(annotation=Literal['azureblob'], required=False, default='azureblob'), 'rclone_config_az_use_msi': FieldInfo(annotation=bool, required=False, default=False)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### rclone_config_az_account *: str | None*

#### rclone_config_az_client_id *: str | None*

#### rclone_config_az_client_secret *: str | None*

#### rclone_config_az_env_auth *: bool*

#### rclone_config_az_key *: str | None*

#### rclone_config_az_sas_url *: str | None*

#### rclone_config_az_tenant *: str | None*

#### rclone_config_az_type *: Literal['azureblob']*

#### rclone_config_az_use_msi *: bool*

### *class* zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonGSSecretSchema(\*, rclone_config_gs_type: Literal['google cloud storage'] = 'google cloud storage', rclone_config_gs_client_id: str | None = None, rclone_config_gs_client_secret: str | None = None, rclone_config_gs_project_number: str | None = None, rclone_config_gs_service_account_credentials: str | None = None, rclone_config_gs_anonymous: bool = False, rclone_config_gs_token: str | None = None, rclone_config_gs_auth_url: str | None = None, rclone_config_gs_token_url: str | None = None)

Bases: [`BaseSecretSchema`](zenml.secret.md#zenml.secret.base_secret.BaseSecretSchema)

Seldon GCS credentials.

Based on: [https://rclone.org/googlecloudstorage/](https://rclone.org/googlecloudstorage/)

Attributes:
: rclone_config_gs_type: the rclone config type. Must be set to “google
  : cloud storage” for this schema.
  <br/>
  rclone_config_gs_client_id: OAuth client id.
  rclone_config_gs_client_secret: OAuth client secret.
  rclone_config_gs_token: OAuth Access Token as a JSON blob.
  rclone_config_gs_project_number: project number.
  rclone_config_gs_service_account_credentials: service account
  <br/>
  > credentials JSON blob.
  <br/>
  rclone_config_gs_anonymous: access public buckets and objects without
  : credentials. Set to True if you just want to download files and
    don’t configure credentials.
  <br/>
  rclone_config_gs_auth_url: auth server URL.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'rclone_config_gs_anonymous': FieldInfo(annotation=bool, required=False, default=False), 'rclone_config_gs_auth_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_gs_client_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_gs_client_secret': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_gs_project_number': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_gs_service_account_credentials': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_gs_token': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_gs_token_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_gs_type': FieldInfo(annotation=Literal['google cloud storage'], required=False, default='google cloud storage')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### rclone_config_gs_anonymous *: bool*

#### rclone_config_gs_auth_url *: str | None*

#### rclone_config_gs_client_id *: str | None*

#### rclone_config_gs_client_secret *: str | None*

#### rclone_config_gs_project_number *: str | None*

#### rclone_config_gs_service_account_credentials *: str | None*

#### rclone_config_gs_token *: str | None*

#### rclone_config_gs_token_url *: str | None*

#### rclone_config_gs_type *: Literal['google cloud storage']*

### *class* zenml.integrations.seldon.secret_schemas.secret_schemas.SeldonS3SecretSchema(\*, rclone_config_s3_type: Literal['s3'] = 's3', rclone_config_s3_provider: str = 'aws', rclone_config_s3_env_auth: bool = False, rclone_config_s3_access_key_id: str | None = None, rclone_config_s3_secret_access_key: str | None = None, rclone_config_s3_session_token: str | None = None, rclone_config_s3_region: str | None = None, rclone_config_s3_endpoint: str | None = None)

Bases: [`BaseSecretSchema`](zenml.secret.md#zenml.secret.base_secret.BaseSecretSchema)

Seldon S3 credentials.

Based on: [https://rclone.org/s3/#amazon-s3](https://rclone.org/s3/#amazon-s3)

Attributes:
: rclone_config_s3_type: the rclone config type. Must be set to “s3” for
  : this schema.
  <br/>
  rclone_config_s3_provider: the S3 provider (e.g. aws, ceph, minio).
  rclone_config_s3_env_auth: get AWS credentials from EC2/ECS meta data
  <br/>
  > (i.e. with IAM roles configuration). Only applies if access_key_id
  > and secret_access_key are blank.
  <br/>
  rclone_config_s3_access_key_id: AWS Access Key ID.
  rclone_config_s3_secret_access_key: AWS Secret Access Key.
  rclone_config_s3_session_token: AWS Session Token.
  rclone_config_s3_region: region to connect to.
  rclone_config_s3_endpoint: S3 API endpoint.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'rclone_config_s3_access_key_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_s3_endpoint': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_s3_env_auth': FieldInfo(annotation=bool, required=False, default=False), 'rclone_config_s3_provider': FieldInfo(annotation=str, required=False, default='aws'), 'rclone_config_s3_region': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_s3_secret_access_key': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_s3_session_token': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_s3_type': FieldInfo(annotation=Literal['s3'], required=False, default='s3')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### rclone_config_s3_access_key_id *: str | None*

#### rclone_config_s3_endpoint *: str | None*

#### rclone_config_s3_env_auth *: bool*

#### rclone_config_s3_provider *: str*

#### rclone_config_s3_region *: str | None*

#### rclone_config_s3_secret_access_key *: str | None*

#### rclone_config_s3_session_token *: str | None*

#### rclone_config_s3_type *: Literal['s3']*

## Module contents

Initialization for the Seldon secret schemas.

These are secret schemas that can be used to authenticate Seldon to the
Artifact Store used to store served ML models.

### *class* zenml.integrations.seldon.secret_schemas.SeldonAzureSecretSchema(\*, rclone_config_az_type: Literal['azureblob'] = 'azureblob', rclone_config_az_env_auth: bool = False, rclone_config_az_account: str | None = None, rclone_config_az_key: str | None = None, rclone_config_az_sas_url: str | None = None, rclone_config_az_use_msi: bool = False, rclone_config_az_client_secret: str | None = None, rclone_config_az_client_id: str | None = None, rclone_config_az_tenant: str | None = None)

Bases: [`BaseSecretSchema`](zenml.secret.md#zenml.secret.base_secret.BaseSecretSchema)

Seldon Azure Blob Storage credentials.

Based on: [https://rclone.org/azureblob/](https://rclone.org/azureblob/)

Attributes:
: rclone_config_az_type: the rclone config type. Must be set to
  : “azureblob” for this schema.
  <br/>
  rclone_config_az_env_auth: read credentials from runtime
  : (environment variables or MSI).
  <br/>
  rclone_config_az_account: storage Account Name. Leave blank to
  : use SAS URL or MSI.
  <br/>
  rclone_config_az_key: storage Account Key. Leave blank to
  : use SAS URL or MSI.
  <br/>
  rclone_config_az_sas_url: SAS URL for container level access
  : only. Leave blank if using account/key or MSI.
  <br/>
  rclone_config_az_use_msi: use a managed service identity to
  : authenticate (only works in Azure).
  <br/>
  rclone_config_az_client_secret: client secret for service
  : principal authentication.
  <br/>
  rclone_config_az_client_id: client id for service principal
  : authentication.
  <br/>
  rclone_config_az_tenant: tenant id for service principal
  : authentication.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'rclone_config_az_account': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_az_client_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_az_client_secret': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_az_env_auth': FieldInfo(annotation=bool, required=False, default=False), 'rclone_config_az_key': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_az_sas_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_az_tenant': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_az_type': FieldInfo(annotation=Literal['azureblob'], required=False, default='azureblob'), 'rclone_config_az_use_msi': FieldInfo(annotation=bool, required=False, default=False)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### rclone_config_az_account *: str | None*

#### rclone_config_az_client_id *: str | None*

#### rclone_config_az_client_secret *: str | None*

#### rclone_config_az_env_auth *: bool*

#### rclone_config_az_key *: str | None*

#### rclone_config_az_sas_url *: str | None*

#### rclone_config_az_tenant *: str | None*

#### rclone_config_az_type *: Literal['azureblob']*

#### rclone_config_az_use_msi *: bool*

### *class* zenml.integrations.seldon.secret_schemas.SeldonGSSecretSchema(\*, rclone_config_gs_type: Literal['google cloud storage'] = 'google cloud storage', rclone_config_gs_client_id: str | None = None, rclone_config_gs_client_secret: str | None = None, rclone_config_gs_project_number: str | None = None, rclone_config_gs_service_account_credentials: str | None = None, rclone_config_gs_anonymous: bool = False, rclone_config_gs_token: str | None = None, rclone_config_gs_auth_url: str | None = None, rclone_config_gs_token_url: str | None = None)

Bases: [`BaseSecretSchema`](zenml.secret.md#zenml.secret.base_secret.BaseSecretSchema)

Seldon GCS credentials.

Based on: [https://rclone.org/googlecloudstorage/](https://rclone.org/googlecloudstorage/)

Attributes:
: rclone_config_gs_type: the rclone config type. Must be set to “google
  : cloud storage” for this schema.
  <br/>
  rclone_config_gs_client_id: OAuth client id.
  rclone_config_gs_client_secret: OAuth client secret.
  rclone_config_gs_token: OAuth Access Token as a JSON blob.
  rclone_config_gs_project_number: project number.
  rclone_config_gs_service_account_credentials: service account
  <br/>
  > credentials JSON blob.
  <br/>
  rclone_config_gs_anonymous: access public buckets and objects without
  : credentials. Set to True if you just want to download files and
    don’t configure credentials.
  <br/>
  rclone_config_gs_auth_url: auth server URL.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'rclone_config_gs_anonymous': FieldInfo(annotation=bool, required=False, default=False), 'rclone_config_gs_auth_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_gs_client_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_gs_client_secret': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_gs_project_number': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_gs_service_account_credentials': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_gs_token': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_gs_token_url': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_gs_type': FieldInfo(annotation=Literal['google cloud storage'], required=False, default='google cloud storage')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### rclone_config_gs_anonymous *: bool*

#### rclone_config_gs_auth_url *: str | None*

#### rclone_config_gs_client_id *: str | None*

#### rclone_config_gs_client_secret *: str | None*

#### rclone_config_gs_project_number *: str | None*

#### rclone_config_gs_service_account_credentials *: str | None*

#### rclone_config_gs_token *: str | None*

#### rclone_config_gs_token_url *: str | None*

#### rclone_config_gs_type *: Literal['google cloud storage']*

### *class* zenml.integrations.seldon.secret_schemas.SeldonS3SecretSchema(\*, rclone_config_s3_type: Literal['s3'] = 's3', rclone_config_s3_provider: str = 'aws', rclone_config_s3_env_auth: bool = False, rclone_config_s3_access_key_id: str | None = None, rclone_config_s3_secret_access_key: str | None = None, rclone_config_s3_session_token: str | None = None, rclone_config_s3_region: str | None = None, rclone_config_s3_endpoint: str | None = None)

Bases: [`BaseSecretSchema`](zenml.secret.md#zenml.secret.base_secret.BaseSecretSchema)

Seldon S3 credentials.

Based on: [https://rclone.org/s3/#amazon-s3](https://rclone.org/s3/#amazon-s3)

Attributes:
: rclone_config_s3_type: the rclone config type. Must be set to “s3” for
  : this schema.
  <br/>
  rclone_config_s3_provider: the S3 provider (e.g. aws, ceph, minio).
  rclone_config_s3_env_auth: get AWS credentials from EC2/ECS meta data
  <br/>
  > (i.e. with IAM roles configuration). Only applies if access_key_id
  > and secret_access_key are blank.
  <br/>
  rclone_config_s3_access_key_id: AWS Access Key ID.
  rclone_config_s3_secret_access_key: AWS Secret Access Key.
  rclone_config_s3_session_token: AWS Session Token.
  rclone_config_s3_region: region to connect to.
  rclone_config_s3_endpoint: S3 API endpoint.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'rclone_config_s3_access_key_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_s3_endpoint': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_s3_env_auth': FieldInfo(annotation=bool, required=False, default=False), 'rclone_config_s3_provider': FieldInfo(annotation=str, required=False, default='aws'), 'rclone_config_s3_region': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_s3_secret_access_key': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_s3_session_token': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'rclone_config_s3_type': FieldInfo(annotation=Literal['s3'], required=False, default='s3')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### rclone_config_s3_access_key_id *: str | None*

#### rclone_config_s3_endpoint *: str | None*

#### rclone_config_s3_env_auth *: bool*

#### rclone_config_s3_provider *: str*

#### rclone_config_s3_region *: str | None*

#### rclone_config_s3_secret_access_key *: str | None*

#### rclone_config_s3_session_token *: str | None*

#### rclone_config_s3_type *: Literal['s3']*
