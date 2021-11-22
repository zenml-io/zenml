#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
from typing import Dict

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

    # TODO [ENG-172]: Write about the materializers
    TYPE_NAME: str = "BaseArtifact"  # type: ignore[assignment]
    PROPERTIES: Dict[str, Property] = {  # type: ignore[assignment]
        MATERIALIZER_PROPERTY_KEY: MATERIALIZER_PROPERTY,
        DATATYPE_PROPERTY_KEY: DATATYPE_PROPERTY,
    }
