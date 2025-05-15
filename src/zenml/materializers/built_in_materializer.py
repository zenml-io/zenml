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
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
from zenml.constants import (
    ENV_ZENML_MATERIALIZER_ALLOW_NON_ASCII_JSON_DUMPS,
    handle_bool_env_var,
)
from zenml.enums import ArtifactType, VisualizationType
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.materializers.materializer_registry import materializer_registry
from zenml.utils import source_utils, yaml_utils

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType

logger = get_logger(__name__)
DEFAULT_FILENAME = "data.json"
DEFAULT_BYTES_FILENAME = "data.txt"
DEFAULT_METADATA_FILENAME = "metadata.json"
BASIC_TYPES = (
    bool,
    float,
    int,
    str,
    type(None),
)  # complex/bytes are not JSON serializable
ZENML_MATERIALIZER_ALLOW_NON_ASCII_JSON_DUMPS = handle_bool_env_var(
    ENV_ZENML_MATERIALIZER_ALLOW_NON_ASCII_JSON_DUMPS, False
)


class BuiltInMaterializer(BaseMaterializer):
    """Handle JSON-serializable basic types (`bool`, `float`, `int`, `str`)."""

    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA
    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = BASIC_TYPES

    def __init__(
        self, uri: str, artifact_store: Optional[BaseArtifactStore] = None
    ):
        """Define `self.data_path`.

        Args:
            uri: The URI where the artifact data is stored.
            artifact_store: The artifact store where the artifact data is stored.
        """
        super().__init__(uri, artifact_store)
        self.data_path = os.path.join(self.uri, DEFAULT_FILENAME)

    def load(
        self, data_type: Union[Type[bool], Type[float], Type[int], Type[str]]
    ) -> Any:
        """Reads basic primitive types from JSON.

        Args:
            data_type: The type of the data to read.

        Returns:
            The data read.
        """
        contents = yaml_utils.read_json(self.data_path)
        if type(contents) is not data_type:
            # TODO [ENG-142]: Raise error or try to coerce
            logger.debug(
                f"Contents {contents} was type {type(contents)} but expected "
                f"{data_type}"
            )
        return contents

    def save(self, data: Union[bool, float, int, str]) -> None:
        """Serialize a basic type to JSON.

        Args:
            data: The data to store.
        """
        yaml_utils.write_json(
            self.data_path,
            data,
            ensure_ascii=not ZENML_MATERIALIZER_ALLOW_NON_ASCII_JSON_DUMPS,
        )

    def save_visualizations(
        self, data: Union[bool, float, int, str]
    ) -> Dict[str, VisualizationType]:
        """Save visualizations for the given basic type.

        Args:
            data: The data to save visualizations for.

        Returns:
            A dictionary of visualization URIs and their types.
        """
        return {self.data_path.replace("\\", "/"): VisualizationType.JSON}

    def extract_metadata(
        self, data: Union[bool, float, int, str]
    ) -> Dict[str, "MetadataType"]:
        """Extract metadata from the given built-in container object.

        Args:
            data: The built-in container object to extract metadata from.

        Returns:
            The extracted metadata as a dictionary.
        """
        # For boolean and numbers, add the string representation as metadata.
        # We don't to this for strings because they can be arbitrarily long.
        if isinstance(data, (bool, float, int)):
            return {"string_representation": str(data)}

        return {}


class BytesMaterializer(BaseMaterializer):
    """Handle `bytes` data type, which is not JSON serializable."""

    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA
    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (bytes,)

    def __init__(
        self, uri: str, artifact_store: Optional[BaseArtifactStore] = None
    ):
        """Define `self.data_path`.

        Args:
            uri: The URI where the artifact data is stored.
            artifact_store: The artifact store where the artifact data is stored.
        """
        super().__init__(uri, artifact_store)
        self.data_path = os.path.join(self.uri, DEFAULT_BYTES_FILENAME)

    def load(self, data_type: Type[Any]) -> Any:
        """Reads a bytes object from file.

        Args:
            data_type: The type of the data to read.

        Returns:
            The data read.
        """
        with self.artifact_store.open(self.data_path, "rb") as file_:
            return file_.read()

    def save(self, data: Any) -> None:
        """Save a bytes object to file.

        Args:
            data: The data to store.
        """
        with self.artifact_store.open(self.data_path, "wb") as file_:
            file_.write(data)

    def save_visualizations(self, data: bytes) -> Dict[str, VisualizationType]:
        """Save visualizations for the given bytes data.

        Args:
            data: The bytes data to save visualizations for.

        Returns:
            A dictionary of visualization URIs and their types.
        """
        return {self.data_path.replace("\\", "/"): VisualizationType.MARKDOWN}


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
    if obj is None:
        return True
    if isinstance(obj, tuple(BASIC_TYPES)):
        return True
    if isinstance(obj, (list, tuple, set)):
        return _all_serializable(obj)
    if isinstance(obj, dict):
        return _all_serializable(obj.keys()) and _all_serializable(
            obj.values()
        )
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
    registered_types = materializer_registry.materializer_types.keys()
    type_str_mapping = {str(type_): type_ for type_ in registered_types}
    if type_str in type_str_mapping:
        return type_str_mapping[type_str]
    raise RuntimeError(f"Cannot resolve type '{type_str}'.")


def find_materializer_registry_type(type_: Type[Any]) -> Type[Any]:
    """For a given type, find the type registered in the registry.

    This can be either the type itself, or a superclass of the type.

    Args:
        type_: The type to find.

    Returns:
        The type registered in the registry.

    Raises:
        RuntimeError: If the type could not be resolved.
    """
    # Check that a unique materializer is registered for this type
    materializer_registry[type_]

    # Check if the type itself is registered
    registered_types = materializer_registry.materializer_types.keys()
    if type_ in registered_types:
        return type_

    # Check if a superclass of the type is registered
    for registered_type in registered_types:
        if issubclass(type_, registered_type):
            return registered_type

    # Raise an error otherwise - this should never happen since
    # `default_materializer_registry[type_]` should have raised an error already
    raise RuntimeError(
        f"Cannot find a materializer for type '{type_}' in the "
        f"materializer registry."
    )


class BuiltInContainerMaterializer(BaseMaterializer):
    """Handle built-in container types (dict, list, set, tuple)."""

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (
        dict,
        list,
        set,
        tuple,
    )

    def __init__(
        self, uri: str, artifact_store: Optional[BaseArtifactStore] = None
    ):
        """Define `self.data_path` and `self.metadata_path`.

        Args:
            uri: The URI where the artifact data is stored.
            artifact_store: The artifact store where the artifact data is stored.
        """
        super().__init__(uri, artifact_store)
        self.data_path = os.path.join(self.uri, DEFAULT_FILENAME)
        self.metadata_path = os.path.join(self.uri, DEFAULT_METADATA_FILENAME)

    def load(self, data_type: Type[Any]) -> Any:
        """Reads a materialized built-in container object.

        If the data was serialized to JSON, deserialize it.

        Otherwise, reconstruct all elements according to the metadata file:
            1. Resolve the data type using `find_type_by_str()`,
            2. Get the materializer via the `default_materializer_registry`,
            3. Initialize the materializer with the desired path,
            4. Use `load()` of that materializer to load the element.

        Args:
            data_type: The type of the data to read.

        Returns:
            The data read.

        Raises:
            RuntimeError: If the data was not found.
        """
        # If the data was not serialized, there must be metadata present.
        if not self.artifact_store.exists(
            self.data_path
        ) and not self.artifact_store.exists(self.metadata_path):
            raise RuntimeError(
                f"Materialization of type {data_type} failed. Expected either"
                f"{self.data_path} or {self.metadata_path} to exist."
            )

        # If the data was serialized as JSON, deserialize it.
        if self.artifact_store.exists(self.data_path):
            outputs = yaml_utils.read_json(self.data_path)

        # Otherwise, use the metadata to reconstruct the data as a list.
        else:
            metadata = yaml_utils.read_json(self.metadata_path)
            outputs = []

            # Backwards compatibility for zenml <= 0.37.0
            if isinstance(metadata, dict):
                for path_, type_str in zip(
                    metadata["paths"], metadata["types"]
                ):
                    type_ = find_type_by_str(type_str)
                    materializer_class = materializer_registry[type_]
                    materializer = materializer_class(
                        uri=path_, artifact_store=self.artifact_store
                    )
                    element = materializer.load(type_)
                    outputs.append(element)

            # New format for zenml > 0.37.0
            elif isinstance(metadata, list):
                for entry in metadata:
                    path_ = entry["path"]
                    type_ = source_utils.load(entry["type"])
                    materializer_class = source_utils.load(
                        entry["materializer"]
                    )
                    materializer = materializer_class(
                        uri=path_, artifact_store=self.artifact_store
                    )
                    element = materializer.load(type_)
                    outputs.append(element)

            else:
                raise RuntimeError(f"Unknown metadata format: {metadata}.")

        # Cast the data to the correct type.
        if issubclass(data_type, dict) and not isinstance(outputs, dict):
            keys, values = outputs
            return data_type(zip(keys, values))
        if issubclass(data_type, tuple) and not isinstance(outputs, tuple):
            return data_type(outputs)
        if issubclass(data_type, set) and not isinstance(outputs, set):
            return data_type(outputs)
        return outputs

    def save(self, data: Any) -> None:
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
        # tuple and set: handle as list.
        if isinstance(data, tuple) or isinstance(data, set):
            data = list(data)

        # If the data is serializable, just write it into a single JSON file.
        if _is_serializable(data):
            yaml_utils.write_json(
                self.data_path,
                data,
                ensure_ascii=not ZENML_MATERIALIZER_ALLOW_NON_ASCII_JSON_DUMPS,
            )
            return

        # non-serializable dict: Handle as non-serializable list of lists.
        if isinstance(data, dict):
            data = [list(data.keys()), list(data.values())]

        # non-serializable list: Materialize each element into a subfolder.
        # Get path, type, and corresponding materializer for each element.
        metadata: List[Dict[str, str]] = []
        materializers: List[BaseMaterializer] = []
        try:
            for i, element in enumerate(data):
                element_path = os.path.join(self.uri, str(i))
                self.artifact_store.mkdir(element_path)
                type_ = type(element)
                materializer_class = materializer_registry[type_]
                materializer = materializer_class(
                    uri=element_path, artifact_store=self.artifact_store
                )
                materializers.append(materializer)
                metadata.append(
                    {
                        "path": element_path,
                        "type": source_utils.resolve(type_).import_path,
                        "materializer": source_utils.resolve(
                            materializer_class
                        ).import_path,
                    }
                )
            # Write metadata as JSON.
            yaml_utils.write_json(self.metadata_path, metadata)
            # Materialize each element.
            for element, materializer in zip(data, materializers):
                materializer.validate_save_type_compatibility(type(element))
                materializer.save(element)
        # If an error occurs, delete all created files.
        except Exception as e:
            # Delete metadata
            if self.artifact_store.exists(self.metadata_path):
                self.artifact_store.remove(self.metadata_path)
            # Delete all elements that were already saved.
            for entry in metadata:
                self.artifact_store.rmtree(entry["path"])
            raise e

    # save dict type objects to JSON file with JSON visualization type
    def save_visualizations(self, data: Any) -> Dict[str, "VisualizationType"]:
        """Save visualizations for the given data.

        Args:
            data: The data to save visualizations for.

        Returns:
            A dictionary of visualization URIs and their types.
        """
        # dict/list type objects are always saved as JSON files
        # doesn't work for non-serializable types as they
        # are saved as list of lists in different files
        if _is_serializable(data):
            return {self.data_path.replace("\\", "/"): VisualizationType.JSON}
        return {}

    def extract_metadata(self, data: Any) -> Dict[str, "MetadataType"]:
        """Extract metadata from the given built-in container object.

        Args:
            data: The built-in container object to extract metadata from.

        Returns:
            The extracted metadata as a dictionary.
        """
        if hasattr(data, "__len__"):
            return {"length": len(data)}
        return {}
