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
from typing import Dict, Type, Union

from zenml.enums import ArtifactType, VisualizationType
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.types import CSVString, HTMLString, MarkdownString

logger = get_logger(__name__)


STRUCTURED_STRINGS = Union[CSVString, HTMLString, MarkdownString]

HTML_FILENAME = "output.html"
MARKDOWN_FILENAME = "output.md"
CSV_FILENAME = "output.csv"


class StructuredStringMaterializer(BaseMaterializer):
    """Materializer for HTML or Markdown strings."""

    ASSOCIATED_TYPES = (CSVString, HTMLString, MarkdownString)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA_ANALYSIS

    def load(self, data_type: Type[STRUCTURED_STRINGS]) -> STRUCTURED_STRINGS:
        """Loads the data from the HTML or Markdown file.

        Args:
            data_type: The type of the data to read.

        Returns:
            The loaded data.
        """
        with fileio.open(self._get_filepath(data_type), "r") as f:
            return data_type(f.read())

    def save(self, data: STRUCTURED_STRINGS) -> None:
        """Save data as an HTML or Markdown file.

        Args:
            data: The data to save as an HTML or Markdown file.
        """
        with fileio.open(self._get_filepath(type(data)), "w") as f:
            f.write(data)

    def save_visualizations(
        self, data: STRUCTURED_STRINGS
    ) -> Dict[str, VisualizationType]:
        """Save visualizations for the given data.

        Args:
            data: The data to save visualizations for.

        Returns:
            A dictionary of visualization URIs and their types.
        """
        filepath = self._get_filepath(type(data))
        visualization_type = self._get_visualization_type(type(data))
        return {filepath: visualization_type}

    def _get_filepath(self, data_type: Type[STRUCTURED_STRINGS]) -> str:
        """Get the file path for the given data type.

        Args:
            data_type: The type of the data.

        Returns:
            The file path for the given data type.

        Raises:
            ValueError: If the data type is not supported.
        """
        if issubclass(data_type, CSVString):
            filename = CSV_FILENAME
        elif issubclass(data_type, HTMLString):
            filename = HTML_FILENAME
        elif issubclass(data_type, MarkdownString):
            filename = MARKDOWN_FILENAME
        else:
            raise ValueError(
                f"Data type {data_type} is not supported by this materializer."
            )
        return os.path.join(self.uri, filename)

    def _get_visualization_type(
        self, data_type: Type[STRUCTURED_STRINGS]
    ) -> VisualizationType:
        """Get the visualization type for the given data type.

        Args:
            data_type: The type of the data.

        Returns:
            The visualization type for the given data type.

        Raises:
            ValueError: If the data type is not supported.
        """
        if issubclass(data_type, CSVString):
            return VisualizationType.CSV
        elif issubclass(data_type, HTMLString):
            return VisualizationType.HTML
        elif issubclass(data_type, MarkdownString):
            return VisualizationType.MARKDOWN
        else:
            raise ValueError(
                f"Data type {data_type} is not supported by this materializer."
            )
