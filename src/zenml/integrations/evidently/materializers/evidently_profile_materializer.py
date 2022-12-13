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
"""Implementation of Evidently profile materializer."""

import os
from typing import Any, Type

from evidently.model_profile import Profile  # type: ignore
from evidently.utils import NumpyEncoder  # type: ignore

from zenml.enums import ArtifactType
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import yaml_utils
from zenml.utils.source_utils import import_class_by_path, resolve_class

logger = get_logger(__name__)

DEFAULT_FILENAME = "profile.json"


class EvidentlyProfileMaterializer(BaseMaterializer):
    """Materializer to read data to and from an Evidently Profile."""

    ASSOCIATED_TYPES = (Profile,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA_ANALYSIS

    def load(self, data_type: Type[Any]) -> Profile:
        """Reads an Evidently Profile object from a json file.

        Args:
            data_type: The type of the data to read.

        Returns:
            The Evidently Profile

        Raises:
            TypeError: if the json file contains an invalid data type.
        """
        super().load(data_type)
        filepath = os.path.join(self.uri, DEFAULT_FILENAME)
        contents = yaml_utils.read_json(filepath)
        if type(contents) != dict:
            raise TypeError(
                f"Contents {contents} was type {type(contents)} but expected "
                f"dictionary"
            )

        section_types = contents.pop("section_types", [])
        sections = []
        for section_type in section_types:
            section_cls = import_class_by_path(section_type)
            section = section_cls()
            section._result = contents[section.part_id()]
            sections.append(section)

        return Profile(sections=sections)

    def save(self, data: Profile) -> None:
        """Serialize an Evidently Profile to a json file.

        Args:
            data: The Evidently Profile to be serialized.
        """
        super().save(data)

        contents = data.object()
        # include the list of profile sections in the serialized dictionary,
        # so we'll be able to re-create them during de-serialization
        contents["section_types"] = [
            resolve_class(stage.__class__) for stage in data.stages
        ]

        filepath = os.path.join(self.uri, DEFAULT_FILENAME)
        yaml_utils.write_json(filepath, contents, encoder=NumpyEncoder)
