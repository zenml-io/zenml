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
from typing import Any, Iterable, Type

from zenml.artifacts import DataAnalysisArtifact, DataArtifact
from zenml.artifacts.base_artifact import BaseArtifact
from zenml.io import fileio
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
BASIC_TYPES = (bool, float, int, str)  # complex/bytes are not JSON serializable


class BuiltInMaterializer(BaseMaterializer):
    """Handle JSON-serializable basic types (`bool`, `float`, `int`, `str`)."""

    ASSOCIATED_ARTIFACT_TYPES = (
        DataArtifact,
        DataAnalysisArtifact,
    )
    ASSOCIATED_TYPES = BASIC_TYPES

    def __init__(self, artifact: "BaseArtifact"):
        """Define `self.data_path`.

        Args:
            artifact: Artifact required by `BaseMaterializer.__init__()`.
        """
        super().__init__(artifact)
        self.data_path = os.path.join(self.artifact.uri, DEFAULT_FILENAME)

    def handle_input(self, data_type: Type[Any]) -> Any:
        """Reads basic primitive types from JSON.

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
        """Serialize a basic type to JSON.

        Args:
            data: The data to store.
        """
        super().handle_return(data)
        yaml_utils.write_json(self.data_path, data)


class BytesMaterializer(BaseMaterializer):
    """Handle `bytes` data type, which is not JSON serializable."""

    ASSOCIATED_ARTIFACT_TYPES = (DataArtifact, DataAnalysisArtifact)
    ASSOCIATED_TYPES = (bytes,)

    def __init__(self, artifact: "BaseArtifact"):
        """Define `self.data_path`.

        Args:
            artifact: Artifact required by `BaseMaterializer.__init__()`.
        """
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


def _all_serializable(iterable: Iterable[Any]) -> bool:
    """For an iterable, check whether all of its elements are JSON-serializable.

    Args:
        iterable (Iterable): The iterable to check.

    Returns:
        True if all elements are JSON-serializable, else False.
    """
    return all(_is_serializable(element) for element in iterable)


def _is_serializable(obj: Any) -> bool:
    """Check whether a built-in object is JSON-serializable.

    Args:
        obj: The object to check.

    Returns:
        True if the entire object is JSON-serializable, else False.
    """
    if isinstance(obj, tuple(BASIC_TYPES)):
        return True
    if isinstance(obj, (list, tuple, set)):
        return _all_serializable(obj)
    if isinstance(obj, dict):
        return _all_serializable(obj.keys()) and _all_serializable(obj.values())
    return False


def find_type_by_str(type_str: str) -> Type[Any]:
    """Get a Python type, given its string representation.

    E.g., "<class 'int'>" should resolve to `int`.

    Currently this is implemented by checking all artifact types registered in
    the `default_materializer_registry`. This means, only types in the registry
    can be found. Any other types will cause a `RunTimeError`.

    Args:
        type_str: The string representation of a type.

    Raises:
        RuntimeError: If the type could not be resolved.

    Returns:
        The type whose string representation is `type_str`.
    """
    # TODO: how to handle subclasses of registered types?
    registered_types = default_materializer_registry.materializer_types.keys()
    type_str_mapping = {str(type_): type_ for type_ in registered_types}
    if type_str in type_str_mapping:
        return type_str_mapping[type_str]
    raise RuntimeError(f"Cannot resolve type '{type_str}'.")


class BuiltInContainerMaterializer(BaseMaterializer):
    """Handle built-in container types (dict, list, set, tuple)."""

    ASSOCIATED_TYPES = (dict, list, set, tuple)

    def __init__(self, artifact: "BaseArtifact"):
        """Define `self.data_path` and `self.metadata_path`.

        Args:
            artifact: Artifact required by `BaseMaterializer.__init__()`.
        """
        super().__init__(artifact)
        self.data_path = os.path.join(self.artifact.uri, DEFAULT_FILENAME)
        self.metadata_path = os.path.join(
            self.artifact.uri, DEFAULT_METADATA_FILENAME
        )

    def handle_input(self, data_type: Type[Any]) -> Any:
        """Reads a materialized built-in container object.

        If the data was serialized to JSON, deserialize it.

        Otherwise, reconstruct all elements according to the metadata file:
            1. Resolve the data type using `find_type_by_str()`,
            2. Get the materializer via the `default_materializer_registry`,
            3. Initialize the materializer with a mock `DataArtifact`, whose
                `uri` attribute is overwritten to point to the desired path,
            4. Use `handle_input()` of that materializer to load the element.

        Args:
            data_type: The type of the data to read.

        Returns:
            The data read.

        Raises:
            RuntimeError: If the data was not found.
        """
        super().handle_input(data_type)

        # If the data was not serialized, there must be metadata present.
        if not fileio.exists(self.data_path) and not fileio.exists(
            self.metadata_path
        ):
            raise RuntimeError(
                f"Materialization of type {data_type} failed. Expected either"
                f"{self.data_path} or {self.metadata_path} to exist."
            )

        # If the data was serialized as JSON, deserialize it.
        if fileio.exists(self.data_path):
            outputs = yaml_utils.read_json(self.data_path)

        # Otherwise, use the metadata to reconstruct the data as a list.
        else:
            metadata = yaml_utils.read_json(self.metadata_path)
            outputs = []
            for path_, type_str in zip(metadata["paths"], metadata["types"]):
                type_ = find_type_by_str(type_str)
                materializer_class = default_materializer_registry[type_]
                mock_artifact = DataArtifact()
                mock_artifact.uri = path_
                materializer = materializer_class(mock_artifact)
                element = materializer.handle_input(type_)
                outputs.append(element)

        # Cast the data to the correct type.
        if issubclass(data_type, dict) and not isinstance(outputs, dict):
            keys, values = outputs
            return dict(zip(keys, values))
        if issubclass(data_type, tuple):
            return tuple(outputs)
        if issubclass(data_type, set):
            return set(outputs)
        return outputs

    def handle_return(self, data: Any) -> None:
        """Materialize a built-in container object.

        If the object can be serialized to JSON, serialize it.

        Otherwise, use the `default_materializer_registry` to find the correct
        materializer for each element and materialize each element into a
        subdirectory.

        Tuples and sets are cast to list before materialization.

        For non-serializable dicts, materialize keys/values as separate lists.

        Args:
            data: The built-in container object to materialize.

        Raises:
            Exception: If any exception occurs, it is raised after cleanup.
        """
        super().handle_return(data)

        # tuple and set: handle as list.
        if isinstance(data, tuple) or isinstance(data, set):
            data = list(data)

        # If the data is serializable, just write it into a single JSON file.
        if _is_serializable(data):
            yaml_utils.write_json(self.data_path, data)

        # non-serializable dict: Handle as non-serializable list of lists.
        if isinstance(data, dict):
            data = [list(data.keys()), list(data.values())]

        # non-serializable list: Materialize each element into a subfolder.
        # Get path, type, and corresponding materializer for each element.
        paths, types, materializers = [], [], []
        for i, element in enumerate(data):
            element_path = os.path.join(self.artifact.uri, str(i))
            fileio.mkdir(element_path)
            type_ = type(element)
            paths.append(element_path)
            types.append(str(type_))
            materializer_class = default_materializer_registry[type_]
            mock_artifact = DataArtifact()
            mock_artifact.uri = element_path
            materializer = materializer_class(mock_artifact)
            materializers.append(materializer)
        try:
            # Write metadata as JSON.
            metadata = {"length": len(data), "paths": paths, "types": types}
            yaml_utils.write_json(self.metadata_path, metadata)
            # Materialize each element.
            for element, materializer in zip(data, materializers):
                materializer.handle_return(element)
        # If an error occurs, delete all created files.
        except Exception as e:
            # Delete metadata
            if fileio.exists(self.metadata_path):
                fileio.remove(self.metadata_path)
            # Delete all elements that were already saved.
            for element_path in paths:
                fileio.rmtree(element_path)
            raise e
