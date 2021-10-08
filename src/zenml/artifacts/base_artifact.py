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
from typing import Any

from tfx.types import Artifact

from zenml.materializers.materializer_factory import MaterializerFactory
from zenml.utils.exceptions import ArtifactInterfaceError


class BaseArtifact(Artifact):
    """Base class for all ZenML artifacts.

    Every implementation of an artifact needs to inherit this class.

    While inheriting from this class there are a few things to consider:

    - Upon creation, each artifact class needs to be given a unique TYPE_NAME.
    - Your artifact can feature different properties under the parameter
        PROPERTIES which will be tracked throughout your pipeline runs.
    - TODO [MEDIUM]: Write about the materializers
    """

    TYPE_NAME = "BaseArtifact"
    PROPERTIES = {}

    @property
    def materializers(self) -> MaterializerFactory:
        """Returns a MaterializerFactory which provides access to all registered materializers."""
        return MaterializerFactory(self)

    @materializers.setter
    def materializers(self, _: Any):
        """Setting the materializers property is not allowed. This method always raises
        an ArtifactInterfaceError with an explanation how to use materializers.
        """
        raise ArtifactInterfaceError(
            "Setting the materializers property on an artifact is not allowed. "
            "To add a custom materializer to read/write artifacts, make sure "
            "to subclass `BaseMaterializer` which will automatically register "
            "it and make it accessible via the MaterializerFactory."
        )
