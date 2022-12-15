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
"""Implementation of the Huggingface datasets materializer."""

import os
from tempfile import TemporaryDirectory, mkdtemp
from typing import Any, Type

from datasets import Dataset, load_from_disk  # type: ignore[attr-defined]
from datasets.dataset_dict import DatasetDict

from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import io_utils

DEFAULT_DATASET_DIR = "hf_datasets"


class HFDatasetMaterializer(BaseMaterializer):
    """Materializer to read data to and from huggingface datasets."""

    ASSOCIATED_TYPES = (Dataset, DatasetDict)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA_ANALYSIS

    def load(self, data_type: Type[Any]) -> Dataset:
        """Reads Dataset.

        Args:
            data_type: The type of the dataset to read.

        Returns:
            The dataset read from the specified dir.
        """
        super().load(data_type)
        temp_dir = mkdtemp()
        io_utils.copy_dir(
            os.path.join(self.uri, DEFAULT_DATASET_DIR),
            temp_dir,
        )
        return load_from_disk(temp_dir)

    def save(self, ds: Type[Any]) -> None:
        """Writes a Dataset to the specified dir.

        Args:
            ds: The Dataset to write.
        """
        super().save(ds)
        temp_dir = TemporaryDirectory()
        path = os.path.join(temp_dir.name, DEFAULT_DATASET_DIR)
        try:
            ds.save_to_disk(path)
            io_utils.copy_dir(
                path,
                os.path.join(self.uri, DEFAULT_DATASET_DIR),
            )
        finally:
            fileio.rmtree(temp_dir.name)
