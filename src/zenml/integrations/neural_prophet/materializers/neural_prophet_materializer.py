#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Implementation of the Neural Prophet materializer."""

import os
from typing import Any, Type

import torch
from neuralprophet import NeuralProphet

from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

# TODO [ENG-794]: The integration consists of a simple materializer that uses the
#  torch load and save methods which is the [current recommended way of storing
#  NeuralProphet models on disk](https://github.com/ourownstory/neural_prophet/issues/27).
#  Update this once a better implementation is exposed.

DEFAULT_FILENAME = "entire_model.pt"


class NeuralProphetMaterializer(BaseMaterializer):
    """Materializer to read/write NeuralProphet models."""

    ASSOCIATED_TYPES = (NeuralProphet,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.MODEL

    def load(self, data_type: Type[Any]) -> NeuralProphet:
        """Reads and returns a NeuralProphet model.

        Args:
            data_type: A NeuralProphet model object.

        Returns:
            A loaded NeuralProphet model.
        """
        super().load(data_type)
        with fileio.open(os.path.join(self.uri, DEFAULT_FILENAME), "rb") as f:
            return torch.load(f)

    def save(self, model: NeuralProphet) -> None:
        """Writes a NeuralProphet model.

        Args:
            model: A NeuralProphet model object.
        """
        super().save(model)
        with fileio.open(os.path.join(self.uri, DEFAULT_FILENAME), "wb") as f:
            torch.save(model, f)
