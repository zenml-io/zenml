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
"""Implementation of ZenML's default materializer.

This is the materializer that is used if no other materializer is registered
for a given data type.
"""

import os
from typing import Any, Type

import cloudpickle

from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer

logger = get_logger(__name__)

DEFAULT_FILENAME = "artifact.pkl"


class DefaultMaterializer(BaseMaterializer):
    """Default materializer using cloudpickle.

    This materializer is used if no other materializer is registered for a
    given data type.
    """

    ASSOCIATED_TYPES = (object,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA

    def load(self, data_type: Type[Any]) -> Any:
        """Reads an artifact from a cloudpickle file.

        Args:
            data_type: The data type of the artifact.

        Returns:
            The loaded artifact data.
        """
        super().load(data_type)
        filepath = os.path.join(self.uri, DEFAULT_FILENAME)
        with fileio.open(filepath, "rb") as fid:
            data = cloudpickle.load(fid)
        return data

    def save(self, data: Any) -> None:
        """Saves an artifact to a cloudpickle file.

        Args:
            data: The data to save.
        """
        super().save(data)

        logger.warning(
            f"No materializer is registered for type `{type(data)}`, so the "
            f"default Pickle materializer was used. Pickle is not production "
            f"ready and should only be used for prototyping as the artifacts "
            f"cannot be loaded under different Python versions. Please "
            f"consider implementing a custom materializer for type "
            f"`{type(data)}` according to the instructions at "
            "https://docs.zenml.io/advanced-guide/pipelines/materializers."
        )

        filepath = os.path.join(self.uri, DEFAULT_FILENAME)
        with fileio.open(filepath, "wb") as fid:
            cloudpickle.dump(data, fid)
