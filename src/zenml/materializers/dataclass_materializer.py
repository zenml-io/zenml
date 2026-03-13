#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Materializer for JSON-serializable dataclasses."""

import hashlib
import inspect
import json
import os
from dataclasses import is_dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Optional, Tuple, Type

from pydantic import TypeAdapter

from zenml.enums import ArtifactType, VisualizationType
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import yaml_utils

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType

DEFAULT_FILENAME = "data.json"


def _is_json_serializable_dataclass_type(data_type: Type[Any]) -> bool:
    """Checks whether a type is a JSON-serializable dataclass type.

    Args:
        data_type: The type to check.

    Returns:
        Whether the type is a dataclass type that Pydantic can serialize
        to JSON.
    """
    if not inspect.isclass(data_type) or not is_dataclass(data_type):
        return False

    try:
        TypeAdapter(data_type).json_schema(mode="serialization")
    except Exception:
        return False

    return True


class DataclassMaterializer(BaseMaterializer):
    """Dataclass materializer."""

    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA
    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (object,)
    # Dataclasses do not share a common base class, so we cannot auto-register
    # it in the registry. Instead, it is manually handled in some special logic
    # in the materializer registry.
    SKIP_REGISTRATION: ClassVar[bool] = True

    @classmethod
    def can_save_type(cls, data_type: Type[Any]) -> bool:
        """Checks whether the materializer can save a data type.

        Args:
            data_type: The type to check.

        Returns:
            Whether the type can be saved.
        """
        return _is_json_serializable_dataclass_type(data_type)

    @classmethod
    def can_load_type(cls, data_type: Type[Any]) -> bool:
        """Checks whether the materializer can load a data type.

        Args:
            data_type: The type to check.

        Returns:
            Whether the type can be loaded.
        """
        return _is_json_serializable_dataclass_type(data_type)

    def load(self, data_type: Type[Any]) -> Any:
        """Reads a dataclass instance from JSON.

        Args:
            data_type: The type of the data to read.

        Returns:
            The deserialized dataclass instance.
        """
        data_path = os.path.join(self.uri, DEFAULT_FILENAME)
        contents = yaml_utils.read_json(data_path)
        return TypeAdapter(data_type).validate_python(contents)

    def save(self, data: Any) -> None:
        """Serializes a dataclass instance to JSON.

        Args:
            data: The dataclass instance to store.
        """
        data_path = os.path.join(self.uri, DEFAULT_FILENAME)
        adapter = TypeAdapter(type(data))
        yaml_utils.write_json(
            data_path,
            adapter.dump_python(data, mode="json"),
        )

    def extract_metadata(self, data: Any) -> Dict[str, "MetadataType"]:
        """Extracts metadata from the given dataclass instance.

        Args:
            data: The dataclass instance to inspect.

        Returns:
            The extracted metadata.
        """
        return {"schema": TypeAdapter(type(data)).json_schema()}

    def compute_content_hash(self, data: Any) -> Optional[str]:
        """Computes a deterministic content hash for the dataclass.

        Args:
            data: The dataclass instance to hash.

        Returns:
            The content hash.
        """
        adapter = TypeAdapter(type(data))
        data = adapter.dump_python(data, mode="json")
        hash_ = hashlib.md5(usedforsecurity=False)
        hash_.update(json.dumps(data, sort_keys=True).encode())
        return hash_.hexdigest()

    def save_visualizations(self, data: Any) -> Dict[str, "VisualizationType"]:
        """Saves JSON visualizations for the given dataclass instance.

        Args:
            data: The dataclass instance to visualize.

        Returns:
            A dictionary of visualization URIs and their types.
        """
        data_path = os.path.join(self.uri, DEFAULT_FILENAME)
        return {data_path.replace("\\", "/"): VisualizationType.JSON}
