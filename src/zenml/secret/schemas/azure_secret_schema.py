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
"""Azure Authentication Secret Schema definition."""

from zenml.secret.base_secret import BaseSecretSchema


class AzureSecretSchema(BaseSecretSchema):
    """Azure Authentication Secret Schema definition."""

    account_name: str | None = None
    account_key: str | None = None
    sas_token: str | None = None
    connection_string: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    tenant_id: str | None = None
