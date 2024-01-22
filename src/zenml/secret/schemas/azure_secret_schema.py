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

from typing import Optional

from zenml.secret.base_secret import BaseSecretSchema


class AzureSecretSchema(BaseSecretSchema):
    """Azure Authentication Secret Schema definition."""

    account_name: Optional[str] = None
    account_key: Optional[str] = None
    sas_token: Optional[str] = None
    connection_string: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    tenant_id: Optional[str] = None
