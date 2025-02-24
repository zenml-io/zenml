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
import io
import gzip
import pickle
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Iterable,
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
from zenml.io import fileio

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
                f"Materialization of type {data_type} failed. Expected either "
                f"{self.data_path} or {self.metadata_path} to exist."
            )

        # If the data was serialized as JSON, deserialize it.
        if self.artifact_store.exists(self.data_path):
            outputs = yaml_utils.read_json(self.data_path)

        # Otherwise, use the metadata to reconstruct the data as a list.
        else:
            metadata = yaml_utils.read_json(self.metadata_path)

            # V3 format (batch compression, introduced for much better I/O performance)
            if isinstance(metadata, dict) and metadata.get("version") == "v3":
                # Pre-allocate a list of the right size
                max_index = (
                    max(element["index"] for element in metadata["elements"])
                    if metadata["elements"]
                    else -1
                )
                outputs = [None] * (max_index + 1)

                # Import required libraries
                import gzip
                import pickle

                # Cache for loaded chunks to avoid loading the same chunk multiple times
                loaded_chunks = {}

                # Process elements in the order they appear in metadata
                for element_info in metadata["elements"]:
                    idx = element_info["index"]
                    batch_id = element_info["batch_id"]

                    # Find the group this element belongs to
                    group = next(
                        (
                            g
                            for g in metadata["groups"]
                            if g["batch_id"] == batch_id
                        ),
                        None,
                    )
                    if not group:
                        raise RuntimeError(
                            f"Cannot find batch group {batch_id} in metadata"
                        )

                    # Find which chunk contains this index
                    chunk_info = None
                    for chunk in group["chunks"]:
                        if idx in chunk["indices"]:
                            chunk_info = chunk
                            break

                    if not chunk_info:
                        raise RuntimeError(
                            f"Cannot find chunk containing index {idx} in batch {batch_id}"
                        )

                    # Load the chunk if not already loaded
                    chunk_path = chunk_info["path"]
                    if chunk_path not in loaded_chunks:
                        with fileio.open(chunk_path, "rb") as f_raw:
                            # Read the compressed data
                            compressed_data = f_raw.read()
                            # Use in-memory buffer for gzip decompression
                            with io.BytesIO(compressed_data) as f_buffer:
                                with gzip.GzipFile(fileobj=f_buffer, mode="rb") as f_gzip:
                                    chunk_data = pickle.load(f_gzip)
                        loaded_chunks[chunk_path] = chunk_data

                    # Find the position of this index in the chunk's indices list
                    chunk_position = chunk_info["indices"].index(idx)

                    # Get the element from the loaded chunk
                    element = loaded_chunks[chunk_path][chunk_position]
                    outputs[idx] = element

            # V2 format (optimized for collections, introduced for better performance)
            elif (
                isinstance(metadata, dict) and metadata.get("version") == "v2"
            ):
                # Pre-allocate a list of the right size
                max_index = (
                    max(element["index"] for element in metadata["elements"])
                    if metadata["elements"]
                    else -1
                )
                outputs = [None] * (max_index + 1)

                # Load all elements
                for element_info in metadata["elements"]:
                    path_ = element_info["path"]
                    type_ = source_utils.load(element_info["type"])
                    materializer_class = source_utils.load(
                        element_info["materializer"]
                    )
                    idx = element_info["index"]

                    materializer = materializer_class(uri=path_)
                    element = materializer.load(type_)
                    outputs[idx] = element

            # Backwards compatibility for zenml <= 0.37.0
            elif isinstance(metadata, dict):
                outputs = []
                for path_, type_str in zip(
                    metadata["paths"], metadata["types"]
                ):
                    type_ = find_type_by_str(type_str)
                    materializer_class = materializer_registry[type_]
                    materializer = materializer_class(uri=path_)
                    element = materializer.load(type_)
                    outputs.append(element)

            # Format for zenml > 0.37.0 and < v2
            elif isinstance(metadata, list):
                outputs = []
                for entry in metadata:
                    path_ = entry["path"]
                    type_ = source_utils.load(entry["type"])
                    materializer_class = source_utils.load(
                        entry["materializer"]
                    )
                    materializer = materializer_class(uri=path_)
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
        materializer for each element and materialize elements efficiently.

        For large collections, elements are grouped by type and processed together
        to improve performance.

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

        # Imports already done at the top of the file

        # Group elements by type to process similar elements together
        # This reduces the overhead of materializer initialization and type checking
        type_groups = {}
        for i, element in enumerate(data):
            element_type = type(element)
            if element_type not in type_groups:
                type_groups[element_type] = []
            type_groups[element_type].append((i, element))

        # Enhanced metadata with format version for backward compatibility
        metadata = {
            "version": "v3",  # Mark this as v3 format with batch compression
            "groups": [],
            "elements": [],
        }

        created_files = []
        try:
            # Process each type group
            for group_idx, (element_type, elements) in enumerate(
                type_groups.items()
            ):
                # Get the materializer class once for all elements of this type
                materializer_class = materializer_registry[element_type]

                # Save type information for all elements in this group
                type_info = source_utils.resolve(element_type).import_path
                materializer_info = source_utils.resolve(
                    materializer_class
                ).import_path

                # Create a batch directory for this type
                batch_id = f"batch_{group_idx}"
                batch_dir = os.path.join(self.uri, batch_id)
                self.artifact_store.mkdir(batch_dir)
                created_files.append(batch_dir)

                # Add group info to metadata
                group_metadata = {
                    "batch_id": batch_id,
                    "type": type_info,
                    "materializer": materializer_info,
                    "indices": [idx for idx, _ in elements],
                    "chunks": [],
                }
                metadata["groups"].append(group_metadata)

                # Process elements in chunks to avoid memory issues with very large collections
                # A reasonable chunk size balances I/O overhead vs memory usage
                CHUNK_SIZE = 100  # Number of elements per chunk file

                for chunk_idx in range(0, len(elements), CHUNK_SIZE):
                    chunk_elements = elements[
                        chunk_idx : chunk_idx + CHUNK_SIZE
                    ]
                    chunk_indices = [idx for idx, _ in chunk_elements]

                    # Create chunk file path
                    chunk_filename = f"chunk_{chunk_idx // CHUNK_SIZE}.pkl.gz"
                    chunk_path = os.path.join(batch_dir, chunk_filename)

                    # Process objects for serialization
                    serialized_items = []

                    for _, element in chunk_elements:
                        # Just validate type compatibility but don't serialize yet
                        materializer = materializer_class(uri="")
                        materializer.validate_save_type_compatibility(
                            element_type
                        )
                        serialized_items.append(element)

                    # Write compressed batch to a single file using ZenML fileio
                    with fileio.open(chunk_path, "wb") as f_raw:
                        # Use in-memory buffer for gzip compression
                        with io.BytesIO() as f_buffer:
                            with gzip.GzipFile(fileobj=f_buffer, mode="wb", compresslevel=6) as f_gzip:
                                pickle.dump(
                                    serialized_items,
                                    f_gzip,
                                    protocol=pickle.HIGHEST_PROTOCOL,
                                )
                            # Get the compressed data
                            compressed_data = f_buffer.getvalue()
                        # Write to the actual storage
                        f_raw.write(compressed_data)

                    created_files.append(chunk_path)

                    # Record chunk information
                    group_metadata["chunks"].append(
                        {
                            "path": chunk_path,
                            "indices": chunk_indices,
                        }
                    )

                # Add individual element references to metadata
                for idx, _ in elements:
                    metadata["elements"].append(
                        {
                            "batch_id": batch_id,
                            "type": type_info,
                            "materializer": materializer_info,
                            "index": idx,  # Store original index for correct ordering
                        }
                    )

            # Write enhanced metadata as JSON
            yaml_utils.write_json(self.metadata_path, metadata)

        # If an error occurs, clean up created files
        except Exception as e:
            # Delete metadata file if it exists
            if self.artifact_store.exists(self.metadata_path):
                self.artifact_store.remove(self.metadata_path)

            # Delete all files created during this process
            for file_path in created_files:
                if self.artifact_store.exists(file_path):
                    if self.artifact_store.isdir(file_path):
                        self.artifact_store.rmtree(file_path)
                    else:
                        self.artifact_store.remove(file_path)

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
