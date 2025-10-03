#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Implementation of ZenML's pydantic materializer."""

import hashlib
import json
import os
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Optional, Tuple, Type

from pydantic import BaseModel

from zenml.enums import ArtifactType, VisualizationType
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import yaml_utils

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType

DEFAULT_FILENAME = "data.json"


class PydanticMaterializer(BaseMaterializer):
    """Handle Pydantic BaseModel objects."""

    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA
    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (BaseModel,)

    def load(self, data_type: Type[BaseModel]) -> Any:
        """Reads BaseModel from JSON.

        Args:
            data_type: The type of the data to read.

        Returns:
            The data read.
        """
        data_path = os.path.join(self.uri, DEFAULT_FILENAME)
        contents = yaml_utils.read_json(data_path)
        return data_type.model_validate_json(contents)

    def save(self, data: BaseModel) -> None:
        """Serialize a BaseModel to JSON.

        Args:
            data: The data to store.
        """
        data_path = os.path.join(self.uri, DEFAULT_FILENAME)
        yaml_utils.write_json(data_path, data.model_dump_json())

    def extract_metadata(self, data: BaseModel) -> Dict[str, "MetadataType"]:
        """Extract metadata from the given BaseModel object.

        Args:
            data: The BaseModel object to extract metadata from.

        Returns:
            The extracted metadata as a dictionary.
        """
        return {"schema": data.schema()}

    def compute_content_hash(self, data: BaseModel) -> Optional[str]:
        """Compute the content hash of the given data.

        Args:
            data: The data to compute the content hash of.

        Returns:
            The content hash of the given data.
        """
        hash_ = hashlib.md5(usedforsecurity=False)
        hash_.update(self.__class__.__name__.encode())

        json_data = data.model_dump(mode="json")
        hash_.update(json.dumps(json_data, sort_keys=True).encode())
        return hash_.hexdigest()

    def save_visualizations(self, data: Any) -> Dict[str, "VisualizationType"]:
        """Save visualizations for the given data.

        Args:
            data: The data to save visualizations for.

        Returns:
            A dictionary of visualization URIs and their types.
        """
        data_path = os.path.join(self.uri, DEFAULT_FILENAME)
        return {data_path.replace("\\", "/"): VisualizationType.JSON}
