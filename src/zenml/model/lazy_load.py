#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Model Version Data Lazy Loader definition."""

from typing import Optional

from pydantic import BaseModel

from zenml.model.model import Model


class ModelVersionDataLazyLoader(BaseModel):
    """Model Version Data Lazy Loader helper class.

    It helps the inner codes to fetch proper artifact,
    model version metadata or artifact metadata from the
    model version during runtime time of the step.
    """

    model: Model
    artifact_name: Optional[str] = None
    artifact_version: Optional[str] = None
    metadata_name: Optional[str] = None
