#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from zenml.model.model_version import ModelVersion


class ModelVersionDataLazyLoader:
    """Model Version Data Lazy Loader helper class.

    It helps the inner codes to fetch proper artifact,
    model version metadata or artifact metadata from the
    model version during runtime time of the step.
    """

    def __init__(
        self,
        model_version: "ModelVersion",
        artifact_name: Optional[str] = None,
        artifact_version: Optional[str] = None,
        metadata_name: Optional[str] = None,
    ):
        """Initialize a ModelVersionDataLazyLoader.

        Args:
            model_version: The model version.
            artifact_name: The artifact name.
            artifact_version: The artifact version.
            metadata_name: The metadata name.
        """
        self.model_version = model_version
        self.artifact_name = artifact_name
        self.artifact_version = artifact_version
        self.metadata_name = metadata_name
