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


class WhylabsCredentialsMixin(SecretReferenceMixin):
    """Mixin class for Whylabs credentials.

    Attributes:
        whylabs_default_org_id: the Whylabs organization ID.
        whylabs_api_key: Whylabs API key.
        whylabs_default_dataset_id: default Whylabs dataset ID to use when
            logging data profiles.
    """

    whylabs_default_org_id: Optional[str] = SecretField()
    whylabs_api_key: Optional[str] = SecretField()
    whylabs_default_dataset_id: Optional[str] = SecretField()

    def get_credentials(self) -> Dict[str, str]:
        """Gets all configured Whylabs credentials.

        Returns:
            The Whylabs credentials.
        """
        keys = (
            "whylabs_default_org_id",
            "whylabs_api_key",
            "whylabs_default_dataset_id",
        )
        return remove_none_values(
            {key: getattr(self, key, None) for key in keys}
        )
