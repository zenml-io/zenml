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

from typing import Optional

from zenml.secret.base_secret import BaseSecretSchema


class WhylabsSecretSchema(BaseSecretSchema):
    """Whylabs credentials.

    Attributes:
        whylabs_default_org_id: the Whylabs organization ID.
        whylabs_api_key: Whylabs API key.
        whylabs_default_dataset_id: default Whylabs dataset ID to use when
            logging data profiles.
    """

    whylabs_default_org_id: str
    whylabs_api_key: str
    whylabs_default_dataset_id: Optional[str] = None
