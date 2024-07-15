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
"""Implementation of the Huggingface datasets materializer."""

import os
from collections import defaultdict
from tempfile import TemporaryDirectory, mkdtemp
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Optional,
    Tuple,
    Type,
    Union,
)

from datasets import Dataset, load_from_disk
from datasets.dataset_dict import DatasetDict

from zenml.enums import ArtifactType, VisualizationType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.materializers.pandas_materializer import PandasMaterializer
from zenml.utils import io_utils

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType

DEFAULT_DATASET_DIR = "hf_datasets"


def extract_repo_name(checksum_str: str) -> Optional[str]:
    """Extracts the repo name from the checksum string.

    An example of a checksum_str is:
    "hf://datasets/nyu-mll/glue@bcdcba79d07bc864c1c254ccfcedcce55bcc9a8c/mrpc/train-00000-of-00001.parquet"
    and the expected output is "nyu-mll/glue".

    Args:
        checksum_str: The checksum_str to extract the repo name from.

    Returns:
        str: The extracted repo name.
    """
    dataset = None
    try:
        parts = checksum_str.split("/")
        if len(parts) >= 4:
            # Case: nyu-mll/glue
            dataset = f"{parts[3]}/{parts[4].split('@')[0]}"
    except Exception:  # pylint: disable=broad-except
        pass

    return dataset


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

    def save_visualizations(
        self, ds: Union[Dataset, DatasetDict]
    ) -> Dict[str, VisualizationType]:
        """Save visualizations for the dataset.

        Args:
            ds: The Dataset or DatasetDict to visualize.

        Returns:
            A dictionary mapping visualization paths to their types.

        Raises:
            ValueError: If the given object is not a `Dataset` or `DatasetDict`.
        """
        visualizations = {}

        if isinstance(ds, Dataset):
            datasets = {"default": ds}
        elif isinstance(ds, DatasetDict):
            datasets = ds
        else:
            raise ValueError(f"Unsupported type {type(ds)}")

        for name, dataset in datasets.items():
            # Generate a unique identifier for the dataset
            if dataset.info.download_checksums:
                dataset_id = extract_repo_name(
                    [x for x in dataset.info.download_checksums.keys()][0]
                )
                if dataset_id:
                    # Create the iframe HTML
                    html = f"""
                    <iframe
                    src="https://huggingface.co/datasets/{dataset_id}/embed/viewer"
                    frameborder="0"
                    width="100%"
                    height="560px"
                    ></iframe>
                    """

                    # Save the HTML to a file
                    visualization_path = os.path.join(
                        self.uri, f"{name}_viewer.html"
                    )
                    with fileio.open(visualization_path, "w") as f:
                        f.write(html)

                    visualizations[visualization_path] = VisualizationType.HTML

        return visualizations
