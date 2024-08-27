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
"""Implementation of Deepchecks dataset materializer."""

from typing import TYPE_CHECKING, Any, ClassVar, Dict, Tuple, Type

from deepchecks.tabular import Dataset

from zenml.enums import ArtifactType, VisualizationType
from zenml.integrations.pandas.materializers.pandas_materializer import (
    PandasMaterializer,
)

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType


class DeepchecksDatasetMaterializer(PandasMaterializer):
    """Materializer to read data to and from Deepchecks dataset."""

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (Dataset,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA

    def load(self, data_type: Type[Any]) -> Dataset:
        """Reads pandas dataframes and creates `deepchecks.Dataset` from it.

        Args:
            data_type: The type of the data to read.

        Returns:
            A Deepchecks Dataset.
        """
        df = super().load(data_type)
        return Dataset(df)

    def save(self, dataset: Dataset) -> None:
        """Serializes pandas dataframe within a `Dataset` object.

        Args:
            dataset: A deepchecks.Dataset object.
        """
        super().save(dataset.data)

    def save_visualizations(
        self, dataset: Dataset
    ) -> Dict[str, VisualizationType]:
        """Saves visualizations for the given Deepchecks dataset.

        Args:
            dataset: The Deepchecks dataset to save visualizations for.

        Returns:
            A dictionary of visualization URIs and their types.
        """
        return super().save_visualizations(dataset.data)

    def extract_metadata(self, dataset: Dataset) -> Dict[str, "MetadataType"]:
        """Extract metadata from the given `Dataset` object.

        Args:
            dataset: The `Dataset` object to extract metadata from.

        Returns:
            The extracted metadata as a dictionary.
        """
        return super().extract_metadata(dataset.data)
