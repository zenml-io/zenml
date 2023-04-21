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
"""Initialization for the post-execution artifact class."""

from typing import Any, Type, cast

from zenml.logger import get_logger
from zenml.models.artifact_models import ArtifactResponseModel
from zenml.models.base_models import BaseResponseModel
from zenml.post_execution.base_view import BaseView

logger = get_logger(__name__)


class ArtifactView(BaseView):
    """Post-execution artifact class.

    This can be used to read artifact data that was created during a pipeline
    execution.
    """

    MODEL_CLASS: Type[BaseResponseModel] = ArtifactResponseModel
    REPR_KEYS = ["id", "name", "uri"]

    @property
    def model(self) -> ArtifactResponseModel:
        """Returns the underlying `ArtifactResponseModel`.

        Returns:
            The underlying `ArtifactResponseModel`.
        """
        return cast(ArtifactResponseModel, self._model)

    def read(self) -> Any:
        """Materializes (loads) the data stored in this artifact.

        Returns:
            The materialized data.
        """
        from zenml.utils.materializer_utils import load_artifact

        return load_artifact(self.model)
