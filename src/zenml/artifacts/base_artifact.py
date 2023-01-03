#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Base class for ZenML artifacts."""


from typing import Optional

from zenml.enums import ArtifactType


class BaseArtifact:
    """Base class for all ZenML artifacts.

    Every implementation of an artifact needs to inherit from this class and be
    given a unique TYPE_NAME.
    """

    TYPE_NAME: str = ArtifactType.BASE

    def __init__(
        self,
        uri: str,
        materializer: Optional[str] = None,
        data_type: Optional[str] = None,
        name: Optional[str] = None,
    ) -> None:
        """Init method for BaseArtifact.

        Args:
            uri: The URI of the artifact.
            materializer: The materializer of the artifact.
            data_type: The data type of the artifact.
            name: The name of the artifact.
        """
        self.uri = uri
        self.materializer = materializer
        self.data_type = data_type
        self.name = name
