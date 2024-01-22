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
"""GCP Authentication Secret Schema definition."""

import json
from typing import Any, Dict

from zenml.secret.base_secret import BaseSecretSchema


class GCPSecretSchema(BaseSecretSchema):
    """GCP Authentication Secret Schema definition."""

    token: str

    def get_credential_dict(self) -> Dict[str, Any]:
        """Gets a dictionary of credentials for authenticating to GCP.

        Returns:
            A dictionary representing GCP credentials.

        Raises:
            ValueError: If the token value is not a JSON string of a dictionary.
        """
        try:
            dict_ = json.loads(self.token)
        except json.JSONDecodeError:
            raise ValueError(
                "Failed to parse GCP secret token. The token value is not a "
                "valid JSON string."
            )

        if not isinstance(dict_, Dict):
            raise ValueError(
                "Failed to parse GCP secret token. The token value does not "
                "represent a GCP credential dictionary."
            )

        return dict_
