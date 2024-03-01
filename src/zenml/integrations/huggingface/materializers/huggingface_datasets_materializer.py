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
from collections import defaultdict
from tempfile import TemporaryDirectory, mkdtemp
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Tuple, Type, Union

from datasets import Dataset, load_from_disk
from datasets.dataset_dict import DatasetDict

from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.materializers.pandas_materializer import PandasMaterializer
from zenml.utils import io_utils

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType

DEFAULT_DATASET_DIR = "hf_datasets"


class HFDatasetMaterializer(BaseMaterializer):
    """Materializer to read data to and from huggingface datasets."""

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (Dataset, DatasetDict)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = (
        ArtifactType.DATA_ANALYSIS
    )

    def load(
        self, data_type: Union[Type[Dataset], Type[DatasetDict]]
    ) -> Union[Dataset, DatasetDict]:
        """Reads Dataset.

        Args:
            data_type: The type of the dataset to read.

        Returns:
            The dataset read from the specified dir.
        """
        temp_dir = mkdtemp()
        io_utils.copy_dir(
            os.path.join(self.uri, DEFAULT_DATASET_DIR),
            temp_dir,
        )
        return load_from_disk(temp_dir)

    def save(self, ds: Union[Dataset, DatasetDict]) -> None:
        """Writes a Dataset to the specified dir.

        Args:
            ds: The Dataset to write.
        """
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

    def extract_metadata(
        self, ds: Union[Dataset, DatasetDict]
    ) -> Dict[str, "MetadataType"]:
        """Extract metadata from the given `Dataset` object.

        Args:
            ds: The `Dataset` object to extract metadata from.

        Returns:
            The extracted metadata as a dictionary.

        Raises:
            ValueError: If the given object is not a `Dataset` or `DatasetDict`.
        """
        pandas_materializer = PandasMaterializer(self.uri)
        if isinstance(ds, Dataset):
            return pandas_materializer.extract_metadata(ds.to_pandas())
        elif isinstance(ds, DatasetDict):
            metadata: Dict[str, Dict[str, "MetadataType"]] = defaultdict(dict)
            for dataset_name, dataset in ds.items():
                dataset_metadata = pandas_materializer.extract_metadata(
                    dataset.to_pandas()
                )
                for key, value in dataset_metadata.items():
                    metadata[key][dataset_name] = value
            return dict(metadata)
        raise ValueError(f"Unsupported type {type(ds)}")
