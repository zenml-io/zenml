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
"""Initialization of secret schemas."""

from zenml.secret.schemas.aws_secret_schema import AWSSecretSchema
from zenml.secret.schemas.azure_secret_schema import AzureSecretSchema
from zenml.secret.schemas.basic_auth_secret_schema import BasicAuthSecretSchema
from zenml.secret.schemas.gcp_secret_schema import GCPSecretSchema

__all__ = [
    "AWSSecretSchema",
    "AzureSecretSchema",
    "BasicAuthSecretSchema",
    "GCPSecretSchema",
]
