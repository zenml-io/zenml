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
"""Implementation for KServe secret schemas."""

from typing import ClassVar, Optional

from typing_extensions import Literal

from zenml.secret import register_secret_schema_class
from zenml.secret.base_secret import BaseSecretSchema

KSERVE_S3_SECRET_SCHEMA_TYPE = "kserve_s3"
KSERVE_GS_SECRET_SCHEMA_TYPE = "kserve_gs"
KSERVE_AZUREBLOB_SECRET_SCHEMA_TYPE = "kserve_az"


@register_secret_schema_class
class KServeS3SecretSchema(BaseSecretSchema):
    """KServe S3 credentials.

    Attributes:
        storage_type: the storage type. Must be set to "s3" for this schema.
        credentials: the credentials to use.
        service_account: the name of the service account.
        s3_endpoint: the S3 endpoint.
        s3_region: the S3 region.
        s3_use_https: whether to use HTTPS.
        s3_verify_ssl: whether to verify SSL.
    """

    TYPE: ClassVar[str] = KSERVE_S3_SECRET_SCHEMA_TYPE

    storage_type: Literal["S3"] = "S3"
    credentials: Optional[str]
    service_account: Optional[str]
    s3_endpoint: Optional[str]
    s3_region: Optional[str]
    s3_use_https: Optional[str]
    s3_verify_ssl: Optional[str]


@register_secret_schema_class
class KServeGSSecretSchema(BaseSecretSchema):
    """KServe GCS credentials.

    Attributes:
        storage_type: the storage type. Must be set to "GCS" for this schema.
        credentials: the credentials to use.
        service_account: the service account.
    """

    TYPE: ClassVar[str] = KSERVE_GS_SECRET_SCHEMA_TYPE

    storage_type: Literal["GCS"] = "GCS"
    credentials: Optional[str]
    service_account: Optional[str]


@register_secret_schema_class
class KServeAzureSecretSchema(BaseSecretSchema):
    """KServe Azure Blob Storage credentials.

    Attributes:
        storage_type: the storage type. Must be set to "GCS" for this schema.
        credentials: the credentials to use.
    """

    TYPE: ClassVar[str] = KSERVE_AZUREBLOB_SECRET_SCHEMA_TYPE

    storage_type: Literal["Azure"] = "Azure"
    credentials: Optional[str]
