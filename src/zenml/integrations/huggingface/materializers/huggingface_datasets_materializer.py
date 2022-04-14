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

import os
from tempfile import TemporaryDirectory
from typing import Any, Type

from datasets import Dataset, load_from_disk  # type: ignore[attr-defined]
from datasets.dataset_dict import DatasetDict

from zenml.artifacts import DataArtifact
from zenml.io import utils as fileio_utils
from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_DATASET_DIR = "hf_datasets"


class HFDatasetMaterializer(BaseMaterializer):
    """Materializer to read data to and from huggingface datasets."""

    ASSOCIATED_TYPES = (Dataset, DatasetDict)
    ASSOCIATED_ARTIFACT_TYPES = (DataArtifact,)

    def handle_input(self, data_type: Type[Any]) -> Dataset:
        """Reads Dataset"""
        super().handle_input(data_type)

        return load_from_disk(
            os.path.join(self.artifact.uri, DEFAULT_DATASET_DIR)
        )

    def handle_return(self, ds: Type[Any]) -> None:
        """Writes a Dataset to the specified dir.
        Args:
            Dataset: The Dataset to write.
        """
        super().handle_return(ds)
        temp_dir = TemporaryDirectory()
        ds.save_to_disk(temp_dir.name)
        fileio_utils.copy_dir(
            temp_dir.name, os.path.join(self.artifact.uri, DEFAULT_DATASET_DIR)
        )
