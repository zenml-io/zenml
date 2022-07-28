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
"""Implementation of ZenML's builtin materializer."""

import os
import shutil
from typing import Any, Iterable, Type

from zenml.artifacts import DataAnalysisArtifact, DataArtifact
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.materializers.default_materializer_registry import (
    default_materializer_registry,
)
from zenml.utils import yaml_utils

logger = get_logger(__name__)
DEFAULT_FILENAME = "data.json"
DEFAULT_BYTES_FILENAME = "data.txt"
DEFAULT_METADATA_FILENAME = "metadata.json"
BASIC_TYPES = (int, str, float, bool)  # complex/bytes are not JSON serializable


class BuiltInMaterializer(BaseMaterializer):
    """Read/Write JSON files."""

    # since these are the 'correct' way to annotate these types.

    ASSOCIATED_ARTIFACT_TYPES = (
        DataArtifact,
        DataAnalysisArtifact,
    )
    ASSOCIATED_TYPES = (*BASIC_TYPES, dict)

    def __init__(self, artifact: "BaseArtifact"):
        super().__init__(artifact)
        self.data_path = os.path.join(self.artifact.uri, DEFAULT_FILENAME)

    def handle_input(self, data_type: Type[Any]) -> Any:
        """Reads basic primitive types from json.

        Args:
            data_type: The type of the data to read.

        Returns:
            The data read.
        """
        super().handle_input(data_type)
        contents = yaml_utils.read_json(self.data_path)
        if type(contents) != data_type:
            # TODO [ENG-142]: Raise error or try to coerce
            logger.debug(
                f"Contents {contents} was type {type(contents)} but expected "
                f"{data_type}"
            )
        return contents

    def handle_return(self, data: Any) -> None:
        """Handles basic built-in types and stores them as json.

        Args:
            data: The data to store.
        """
        super().handle_return(data)
        yaml_utils.write_json(self.data_path, data)


class BytesMaterializer(BaseMaterializer):
    """Handle `bytes` data type, which is not JSON serializable."""

    ASSOCIATED_ARTIFACT_TYPES = (DataArtifact, DataAnalysisArtifact)
    ASSOCIATED_TYPES = [bytes]

    def __init__(self, artifact: "BaseArtifact"):
        super().__init__(artifact)
        self.data_path = os.path.join(self.artifact.uri, DEFAULT_BYTES_FILENAME)

    def handle_input(self, data_type: Type[Any]) -> Any:
        """Reads a bytes object from file.

        Args:
            data_type: The type of the data to read.

        Returns:
            The data read.
        """
        super().handle_input(data_type)
        with open(self.data_path, "rb") as file_:
            return file_.read()

    def handle_return(self, data: Any) -> None:
        """Save a bytes object to file.

        Args:
            data: The data to store.
        """
        super().handle_return(data)
        with open(self.data_path, "wb") as file_:
            file_.write(data)


def _all_builtin(iterable: Iterable):
    return all(_is_pure_builtin_type(element) for element in iterable)


def _is_pure_builtin_type(obj: Any):
    if any(isinstance(obj, basic_type) for basic_type in BASIC_TYPES):
        return True
    if any(isinstance(obj, iterable_) for iterable_ in (list, tuple)):
        return _all_builtin(obj)
    if isinstance(obj, dict):
        return _all_builtin(obj.keys()) and _all_builtin(obj.values())
    return False


def find_type_by_str(type_str: str) -> Type[Any]:
    # TODO: how to handle subclasses of registered types?
    registered_types = default_materializer_registry.materializer_types.keys()
    type_str_mapping = {str(type_): type_ for type_ in registered_types}
    if type_str in type_str_mapping:
        return type_str_mapping[type_str]
    raise RuntimeError(f"Cannot resolve type '{type_str}'.")


class ListMaterializer(BuiltInMaterializer):
    """Read/Write JSON files."""

    ASSOCIATED_TYPES = (list, tuple)

    def __init__(self, artifact: "BaseArtifact"):
        super().__init__(artifact)
        self.metadata_path = os.path.join(
            self.artifact.uri, DEFAULT_METADATA_FILENAME
        )

    def handle_input(self, data_type: Type[Any]) -> Any:
        if os.path.exists(self.data_path):  # list of only built-in types
            outputs = super().handle_input(data_type)
            return tuple(outputs) if data_type == tuple else outputs
        if not os.path.exists(self.metadata_path):
            raise RuntimeError(
                f"Materialization of type {data_type} failed. Expected either"
                f"{self.data_path} or {self.metadata_path} to exist."
            )

        # Reconstruct list from metadata
        metadata = yaml_utils.read_json(self.metadata_path)
        outputs = []
        for element_path, type_str in zip(metadata["paths"], metadata["types"]):
            type_ = find_type_by_str(type_str)
            materializer_class = default_materializer_registry[type_]
            mock_artifact = DataArtifact()
            mock_artifact.uri = element_path
            materializer = materializer_class(mock_artifact)
            element = materializer.handle_input(type_)
            outputs.append(element)
        return tuple(outputs) if data_type == tuple else outputs

    def handle_return(self, data: Any) -> None:
        if _is_pure_builtin_type(data):
            return super().handle_return(data)

        BaseMaterializer.handle_return(self, data)

        # Define metadata and create a list of per-element materializers
        metadata = {"length": len(data), "paths": [], "types": []}
        materializers = []
        for i, element in enumerate(data):
            element_path = os.path.join(self.artifact.uri, str(i))
            os.mkdir(element_path)
            type_ = type(element)
            metadata["paths"].append(element_path)
            metadata["types"].append(str(type_))
            materializer_class = default_materializer_registry[type_]
            mock_artifact = DataArtifact()
            mock_artifact.uri = element_path
            materializer = materializer_class(mock_artifact)
            materializers.append(materializer)

        # Write metadata and materialize each element
        try:
            yaml_utils.write_json(self.metadata_path, metadata)
            for element, materializer in zip(data, materializers):
                materializer.handle_return(element)
        except Exception as e:  # If an error occurs, delete all created files
            # Delete metadata
            if os.path.exists(self.metadata_path):
                os.remove(self.metadata_path)
            # Delete all elements that were already saved
            for element_path in metadata["paths"]:
                shutil.rmtree(element_path)
            raise e
