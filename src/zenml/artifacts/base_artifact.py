# Copyright 2019 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
"""The below code is copied from the TFX source repo with minor changes.
All credits go to the TFX team for the core implementation"""
from typing import Any, Dict

from ml_metadata.proto import metadata_store_pb2
from tfx.types.artifact import Artifact, Property, PropertyType

from zenml.artifacts.constants import (
    DATATYPE_PROPERTY_KEY,
    MATERIALIZER_PROPERTY_KEY,
)

MATERIALIZER_PROPERTY = Property(type=PropertyType.STRING)  # type: ignore[no-untyped-call] # noqa
DATATYPE_PROPERTY = Property(type=PropertyType.STRING)  # type: ignore[no-untyped-call] # noqa


class BaseArtifact(Artifact):
    """Base class for all ZenML artifacts.

    Every implementation of an artifact needs to inherit this class.

    While inheriting from this class there are a few things to consider:

    - Upon creation, each artifact class needs to be given a unique TYPE_NAME.
    - Your artifact can feature different properties under the parameter
        PROPERTIES which will be tracked throughout your pipeline runs.
    """

    TYPE_NAME: str = "BaseArtifact"  # type: ignore[assignment]
    PROPERTIES: Dict[str, Property] = {  # type: ignore[assignment]
        MATERIALIZER_PROPERTY_KEY: MATERIALIZER_PROPERTY,
        DATATYPE_PROPERTY_KEY: DATATYPE_PROPERTY,
    }
    _MLMD_ARTIFACT_TYPE: Any = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init method for BaseArtifact"""
        self.set_zenml_artifact_type()
        super(BaseArtifact, self).__init__(*args, **kwargs)

    @classmethod
    def set_zenml_artifact_type(cls) -> None:
        """Set the type of the artifact."""
        type_name = cls.TYPE_NAME
        if not (type_name and isinstance(type_name, str)):
            raise ValueError(
                (
                    "The Artifact subclass %s must override the TYPE_NAME attribute "
                    "with a string type name identifier (got %r instead)."
                )
                % (cls, type_name)
            )
        artifact_type = metadata_store_pb2.ArtifactType()
        artifact_type.name = type_name
        if cls.PROPERTIES:
            # Perform validation on PROPERTIES dictionary.
            if not isinstance(cls.PROPERTIES, dict):
                raise ValueError(
                    "Artifact subclass %s.PROPERTIES is not a dictionary." % cls
                )
            for key, value in cls.PROPERTIES.items():
                if not (
                    isinstance(key, (str, bytes))
                    and isinstance(value, Property)
                ):
                    raise ValueError(
                        (
                            "Artifact subclass %s.PROPERTIES dictionary must have keys of "
                            "type string and values of type artifact.Property."
                        )
                        % cls
                    )

            # Populate ML Metadata artifact properties dictionary.
            for key, value in cls.PROPERTIES.items():
                artifact_type.properties[
                    key
                ] = value.mlmd_type()  # type: ignore[no-untyped-call]
        cls._MLMD_ARTIFACT_TYPE = artifact_type
