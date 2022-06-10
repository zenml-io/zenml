#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Implementation for Seldon secret schemas."""

from typing import ClassVar, Optional

from typing_extensions import Literal

from zenml.secret import register_secret_schema_class
from zenml.secret.base_secret import BaseSecretSchema

SELDON_S3_SECRET_SCHEMA_TYPE = "seldon_s3"
SELDON_GS_SECRET_SCHEMA_TYPE = "seldon_gs"
SELDON_AZUREBLOB_SECRET_SCHEMA_TYPE = "seldon_az"


@register_secret_schema_class
class SeldonS3SecretSchema(BaseSecretSchema):
    """Seldon S3 credentials.

    Based on: https://rclone.org/s3/#amazon-s3

    Attributes:
        rclone_config_s3_type: the rclone config type. Must be set to "s3" for
            this schema.
        rclone_config_s3_provider: the S3 provider (e.g. aws, ceph, minio).
        rclone_config_s3_env_auth: get AWS credentials from EC2/ECS meta data
            (i.e. with IAM roles configuration). Only applies if access_key_id
            and secret_access_key are blank.
        rclone_config_s3_access_key_id: AWS Access Key ID.
        rclone_config_s3_secret_access_key: AWS Secret Access Key.
        rclone_config_s3_session_token: AWS Session Token.
        rclone_config_s3_region: region to connect to.
        rclone_config_s3_endpoint: S3 API endpoint.

    """

    TYPE: ClassVar[str] = SELDON_S3_SECRET_SCHEMA_TYPE

    rclone_config_s3_type: Literal["s3"] = "s3"
    rclone_config_s3_provider: str = "aws"
    rclone_config_s3_env_auth: bool = False
    rclone_config_s3_access_key_id: Optional[str]
    rclone_config_s3_secret_access_key: Optional[str]
    rclone_config_s3_session_token: Optional[str]
    rclone_config_s3_region: Optional[str]
    rclone_config_s3_endpoint: Optional[str]


@register_secret_schema_class
class SeldonGSSecretSchema(BaseSecretSchema):
    """Seldon GCS credentials.

    Based on: https://rclone.org/googlecloudstorage/

    Attributes:
        rclone_config_gs_type: the rclone config type. Must be set to "google
            cloud storage" for this schema.
        rclone_config_gs_client_id: OAuth client id.
        rclone_config_gs_client_secret: OAuth client secret.
        rclone_config_gs_token: OAuth Access Token as a JSON blob.
        rclone_config_gs_project_number: project number.
        rclone_config_gs_service_account_credentials: service account
            credentials JSON blob.
        rclone_config_gs_anonymous: access public buckets and objects without
            credentials. Set to True if you just want to download files and
            don't configure credentials.
        rclone_config_gs_auth_url: auth server URL.
    """

    TYPE: ClassVar[str] = SELDON_GS_SECRET_SCHEMA_TYPE

    rclone_config_gs_type: Literal[
        "google cloud storage"
    ] = "google cloud storage"
    rclone_config_gs_client_id: Optional[str]
    rclone_config_gs_client_secret: Optional[str]
    rclone_config_gs_project_number: Optional[str]
    rclone_config_gs_service_account_credentials: Optional[str]
    rclone_config_gs_anonymous: bool = False
    rclone_config_gs_token: Optional[str]
    rclone_config_gs_auth_url: Optional[str]
    rclone_config_gs_token_url: Optional[str]


@register_secret_schema_class
class SeldonAzureSecretSchema(BaseSecretSchema):
    """Seldon Azure Blob Storage credentials.

    Based on: https://rclone.org/azureblob/

    Attributes:
        rclone_config_azureblob_type: the rclone config type. Must be set to
            "azureblob" for this schema.
        rclone_config_azureblob_account: storage Account Name. Leave blank to
            use SAS URL or MSI.
        rclone_config_azureblob_key: storage Account Key. Leave blank to
            use SAS URL or MSI.
        rclone_config_azureblob_sas_url: SAS URL for container level access
            only. Leave blank if using account/key or MSI.
        rclone_config_azureblob_use_msi: use a managed service identity to
            authenticate (only works in Azure).
    """

    TYPE: ClassVar[str] = SELDON_AZUREBLOB_SECRET_SCHEMA_TYPE

    rclone_config_azureblob_type: Literal["azureblob"] = "azureblob"
    rclone_config_azureblob_account: Optional[str]
    rclone_config_azureblob_key: Optional[str]
    rclone_config_azureblob_sas_url: Optional[str]
    rclone_config_azureblob_use_msi: bool = False
