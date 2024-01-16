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
"""Pipeline utilities to support Model Control Plane."""

from typing import List, Optional

from pydantic import BaseModel, PrivateAttr

from zenml.model.model_version import ModelVersion


class NewModelVersionRequest(BaseModel):
    """Request to create a new model version."""

    class Requester(BaseModel):
        """Requester of a new model version."""

        source: str
        name: str

        def __repr__(self) -> str:
            """Return a string representation of the requester.

            Returns:
                A string representation of the requester.
            """
            return f"{self.source}::{self.name}"

    requesters: List[Requester] = []
    _model_version: Optional[ModelVersion] = PrivateAttr(default=None)

    @property
    def model_version(self) -> ModelVersion:
        """Model version getter.

        Returns:
            The model version.

        Raises:
            RuntimeError: If the model version is not set.
        """
        if self._model_version is None:
            raise RuntimeError("Model version is not set.")
        return self._model_version

    def update_request(
        self,
        model_version: ModelVersion,
        requester: "NewModelVersionRequest.Requester",
    ) -> None:
        """Update from `ModelVersion` in place.

        Args:
            model_version: `ModelVersion` to use.
            requester: Requester of a new model version.
        """
        self.requesters.append(requester)
        if self._model_version is None:
            self._model_version = model_version

        self._model_version._merge(model_version)
