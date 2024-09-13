# zenml.integrations.label_studio.steps package

## Submodules

## zenml.integrations.label_studio.steps.label_studio_standard_steps module

Implementation of standard steps for the Label Studio annotator integration.

### *class* zenml.integrations.label_studio.steps.label_studio_standard_steps.LabelStudioDatasetSyncParameters(\*, storage_type: str = 'local', label_config_type: str, prefix: str | None = None, regex_filter: str | None = '.\*', use_blob_urls: bool | None = True, presign: bool | None = True, presign_ttl: int | None = 1, description: str | None = '', azure_account_name: str | None = None, azure_account_key: str | None = None, google_application_credentials: str | None = None, aws_access_key_id: str | None = None, aws_secret_access_key: str | None = None, aws_session_token: str | None = None, s3_region_name: str | None = None, s3_endpoint: str | None = None)

Bases: `BaseModel`

Step parameters when syncing data to Label Studio.

Attributes:
: storage_type: The type of storage to sync to. Can be one of
  : [“gcs”, “s3”, “azure”, “local”]. Defaults to “local”.
  <br/>
  label_config_type: The type of label config to use.
  prefix: Specify the prefix within the cloud store to import your data
  <br/>
  > from. For local storage, this is the full absolute path to the
  > directory containing your data.
  <br/>
  regex_filter: Specify a regex filter to filter the files to import.
  use_blob_urls: Specify whether your data is raw image or video data, or
  <br/>
  > JSON tasks.
  <br/>
  presign: Specify whether or not to create presigned URLs.
  presign_ttl: Specify how long to keep presigned URLs active.
  description: Specify a description for the dataset.
  <br/>
  azure_account_name: Specify the Azure account name to use for the
  : storage.
  <br/>
  azure_account_key: Specify the Azure account key to use for the
  : storage.
  <br/>
  google_application_credentials: Specify the file with Google application
  : credentials to use for the storage.
  <br/>
  aws_access_key_id: Specify the AWS access key ID to use for the
  : storage.
  <br/>
  aws_secret_access_key: Specify the AWS secret access key to use for the
  : storage.
  <br/>
  aws_session_token: Specify the AWS session token to use for the
  : storage.
  <br/>
  s3_region_name: Specify the S3 region name to use for the storage.
  s3_endpoint: Specify the S3 endpoint to use for the storage.

#### aws_access_key_id *: str | None*

#### aws_secret_access_key *: str | None*

#### aws_session_token *: str | None*

#### azure_account_key *: str | None*

#### azure_account_name *: str | None*

#### description *: str | None*

#### google_application_credentials *: str | None*

#### label_config_type *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'aws_access_key_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'aws_secret_access_key': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'aws_session_token': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'azure_account_key': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'azure_account_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=''), 'google_application_credentials': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'label_config_type': FieldInfo(annotation=str, required=True), 'prefix': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'presign': FieldInfo(annotation=Union[bool, NoneType], required=False, default=True), 'presign_ttl': FieldInfo(annotation=Union[int, NoneType], required=False, default=1), 'regex_filter': FieldInfo(annotation=Union[str, NoneType], required=False, default='.\*'), 's3_endpoint': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 's3_region_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'storage_type': FieldInfo(annotation=str, required=False, default='local'), 'use_blob_urls': FieldInfo(annotation=Union[bool, NoneType], required=False, default=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### prefix *: str | None*

#### presign *: bool | None*

#### presign_ttl *: int | None*

#### regex_filter *: str | None*

#### s3_endpoint *: str | None*

#### s3_region_name *: str | None*

#### storage_type *: str*

#### use_blob_urls *: bool | None*

## Module contents

Standard steps to be used with the Label Studio annotator integration.
