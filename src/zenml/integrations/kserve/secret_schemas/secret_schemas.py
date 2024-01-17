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

from typing import Optional

from zenml.secret.base_secret import BaseSecretSchema


class KServeS3SecretSchema(BaseSecretSchema):
    """KServe S3 credentials.

    Attributes:
        aws_access_key_id: the AWS access key ID.
        aws_secret_access_key: the AWS secret access key.
        s3_endpoint: the S3 endpoint.
        s3_region: the S3 region.
        s3_use_https: whether to use HTTPS.
        s3_verify_ssl: whether to verify SSL.
    """

    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    s3_endpoint: Optional[str] = None
    s3_region: Optional[str] = None
    s3_use_https: Optional[str] = None
    s3_verify_ssl: Optional[str] = None


class KServeGSSecretSchema(BaseSecretSchema):
    """KServe GCS credentials.

    Attributes:
        google_application_credentials: the GCP application credentials to use,
            in JSON format.
    """

    google_application_credentials: Optional[str]


class KServeAzureSecretSchema(BaseSecretSchema):
    """KServe Azure Blob Storage credentials.

    Attributes:
        azure_client_id: the Azure client ID.
        azure_client_secret: the Azure client secret.
        azure_tenant_id: the Azure tenant ID.
        azure_subscription_id: the Azure subscription ID.
    """

    azure_client_id: Optional[str] = None
    azure_client_secret: Optional[str] = None
    azure_tenant_id: Optional[str] = None
    azure_subscription_id: Optional[str] = None
