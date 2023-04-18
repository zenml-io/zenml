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
"""Implementation of HTMLString materializer."""

import os
from typing import Dict, Type

from zenml.enums import ArtifactType, VisualizationType
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.types import HTMLString

logger = get_logger(__name__)

DEFAULT_FILENAME = "output.html"


class HTMLStringMaterializer(BaseMaterializer):
    """Materializer to save data to and from an HTML file."""

    ASSOCIATED_TYPES = (HTMLString,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA_ANALYSIS

    def __init__(self, uri: str):
        """Initializes the HTML materializer.

        Args:
            uri: The URI where the artifact data is stored.
        """
        super().__init__(uri)
        self.data_path = os.path.join(self.uri, DEFAULT_FILENAME)

    def load(self, data_type: Type[HTMLString]) -> HTMLString:
        """Loads the data from the HTML file.

        Args:
            data_type: The type of the data to read.

        Returns:
            The data read from the HTML file.
        """
        super().load(data_type)
        with open(self.data_path, "r") as f:
            return HTMLString(f.read())

    def save(self, data: HTMLString) -> None:
        """Saves the data as an HTML file.

        Args:
            data: The data to save as an HTML file.
        """
        super().save(data)
        with open(self.data_path, "w") as f:
            f.write(data)

    def save_visualizations(
        self, data: HTMLString
    ) -> Dict[str, VisualizationType]:
        """Save visualizations for the given data.

        Args:
            data: The data to save visualizations for.

        Returns:
            A dictionary of visualization URIs and their types.
        """
        visualizations = super().save_visualizations(data)
        visualizations[self.data_path] = VisualizationType.HTML
        return visualizations
