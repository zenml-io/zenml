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
"""Azure credentials mixin."""

from typing import Dict, Optional

from zenml.config.secret_reference_mixin import SecretReferenceMixin
from zenml.utils.dict_utils import remove_none_values
from zenml.utils.secret_utils import SecretField


class AzureCredentialsMixin(SecretReferenceMixin):
    """Mixin class for Azure credentials."""

    account_name: Optional[str] = SecretField()
    account_key: Optional[str] = SecretField()
    sas_token: Optional[str] = SecretField()
    connection_string: Optional[str] = SecretField()
    client_id: Optional[str] = SecretField()
    client_secret: Optional[str] = SecretField()
    tenant_id: Optional[str] = SecretField()

    def get_credentials(self) -> Dict[str, str]:
        """Gets all configured Azure credentials.

        Returns:
            The Azure credentials.
        """
        keys = (
            "account_name",
            "account_key",
            "sas_token",
            "connection_string",
            "client_id",
            "client_secret",
            "tenant_id",
        )
        return remove_none_values(
            {key: getattr(self, key, None) for key in keys}
        )
