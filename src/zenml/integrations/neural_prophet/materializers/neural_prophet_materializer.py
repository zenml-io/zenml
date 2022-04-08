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

import os
from typing import Any, Type

import torch
from neuralprophet import NeuralProphet

from zenml.artifacts import ModelArtifact
from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "entire_model.pt"


class NeuralProphetMaterializer(BaseMaterializer):
    """Materializer to read/write NeuralProphet models."""

    ASSOCIATED_TYPES = (NeuralProphet,)
    ASSOCIATED_ARTIFACT_TYPES = (ModelArtifact,)

    def handle_input(self, data_type: Type[Any]) -> NeuralProphet:
        """Reads and retuPrns a NeuralProphet model.

        Returns:
            A loaded NeuralProphet model.
        """
        super().handle_input(data_type)
        return torch.load(  # type: ignore[no-untyped-call]
            os.path.join(self.artifact.uri, DEFAULT_FILENAME)
        )  # noqa

    def handle_return(self, model: NeuralProphet) -> None:
        """Writes a NeuralProphet model.

        Args:
            model: A torch.nn.Module or a dict to pass into model.save
        """
        super().handle_return(model)
        torch.save(model, os.path.join(self.artifact.uri, DEFAULT_FILENAME))
