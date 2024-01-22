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

from zenml.model.model import Model


class NewModelRequest(BaseModel):
    """Request to create a new version of a model."""

    class Requester(BaseModel):
        """Requester of a new version of a model."""

        source: str
        name: str

        def __repr__(self) -> str:
            """Return a string representation of the requester.

            Returns:
                A string representation of the requester.
            """
            return f"{self.source}::{self.name}"

    requesters: List[Requester] = []
    _model: Optional[Model] = PrivateAttr(default=None)

    @property
    def model(self) -> Model:
        """Model getter.

        Returns:
            The model.

        Raises:
            RuntimeError: If the model is not set.
        """
        if self._model is None:
            raise RuntimeError("Model is not set.")
        return self._model

    def update_request(
        self,
        model: Model,
        requester: "NewModelRequest.Requester",
    ) -> None:
        """Update from `Model` in place.

        Args:
            model: `Model` to use.
            requester: Requester of a new version of a model.
        """
        self.requesters.append(requester)
        if self._model is None:
            self._model = model

        self._model._merge(model)
